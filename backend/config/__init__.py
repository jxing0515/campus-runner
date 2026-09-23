"""让 Django 使用纯 Python 的 PyMySQL 驱动，无需编译 mysqlclient。"""
import pymysql

pymysql.install_as_MySQLdb()
