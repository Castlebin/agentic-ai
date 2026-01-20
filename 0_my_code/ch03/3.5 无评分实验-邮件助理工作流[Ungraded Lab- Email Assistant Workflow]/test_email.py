import utils
import email_tools

# 注意，先启动邮件服务端    python email_service.py

# 取消注释你想尝试的 'utils.test_*' 行
new_email_id = utils.test_send_email()
r1 = utils.test_get_email(new_email_id['id'])
r2 = utils.test_list_emails()
r3 = utils.test_filter_emails(recipient="test@example.com")
r4 = utils.test_search_emails("hr")
r5 = utils.test_unread_emails()
r6 = utils.test_mark_read(new_email_id['id'])
r7 = utils.test_mark_unread(new_email_id['id'])
r8 = utils.test_delete_email(new_email_id['id'])
r9 = utils.reset_database()


s1 = email_tools.list_unread_emails()
s2 = email_tools.search_emails("hr")
s3 = email_tools.search_unread_from_sender("hr@company.com")



print("")

