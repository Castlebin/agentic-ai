"""
使用替代服务的天气函数，解决了原ipinfo.io服务在中国大陆可能无法访问的问题
"""

import requests


def get_weather_from_ip():
    """
    通过IP地址获取用户位置的天气信息（华氏温度）
    使用替代的地理位置服务以提高在中国大陆的可用性
    """
    # 尝试多个IP地理位置服务，按优先级排序
    geo_services = [
        {
            'url': 'https://ipapi.co/json/',
            'extractor': lambda data: data['latlong'].split(',')
        },
        {
            'url': 'https://freegeoip.app/json/',
            'extractor': lambda data: [str(data['latitude']), str(data['longitude'])]
        },
        {
            'url': 'https://ipgeolocation.io/ipgeo-api.php?apiKey=free',
            'extractor': lambda data: [data['latitude'], data['longitude']]
        },
        {
            'url': 'https://json.geoiplookup.io/',
            'extractor': lambda data: [str(data['latitude']), str(data['longitude'])]
        }
    ]

    lat = None
    lon = None
    
    # 尝试各个服务直到成功
    for service in geo_services:
        try:
            response = requests.get(service['url'], timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 验证返回的数据是否有效
            coords = service['extractor'](data)
            if len(coords) >= 2 and coords[0] and coords[1]:
                lat, lon = coords[0].strip(), coords[1].strip()
                if lat != '0' or lon != '0':  # 确保不是默认坐标
                    print(f"成功获取地理位置: {lat}, {lon}, {service['url']}")
                    break
        except Exception:
            continue  # 如果当前服务失败，尝试下一个

    # 如果所有地理位置服务都失败，使用默认坐标（北京）
    if not lat or not lon:
        lat, lon = "39.9042", "116.4074"  # 北京坐标作为备用
        print("警告: 无法获取精确的地理位置，使用默认位置（北京）")

    try:
        # 设置天气 API 调用的参数
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }

        # 获取天气数据
        weather_response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        # 格式化并返回简洁字符串
        return (
            f"Current: {weather_data['current']['temperature_2m']}°F, "
            f"High: {weather_data['daily']['temperature_2m_max'][0]}°F, "
            f"Low: {weather_data['daily']['temperature_2m_min'][0]}°F"
        )
    except requests.exceptions.ConnectionError:
        return "无法连接到天气服务，请检查网络连接。"
    except requests.exceptions.Timeout:
        return "获取天气信息超时，请稍后重试。"
    except requests.exceptions.RequestException as e:
        return f"获取天气信息时发生错误: {str(e)}"
    except KeyError as e:
        return f"无法从服务响应中获取有效的天气数据: {str(e)}"
    except Exception as e:
        return f"获取天气信息时发生未知错误: {str(e)}"


# 示例用法
if __name__ == "__main__":
    weather_info = get_weather_from_ip()
    print(weather_info)