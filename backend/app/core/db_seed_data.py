"""
数据库初始化所需的种子数据
"""

DEFAULT_USERS = [
    {
        "id": 1,
        "username": "system_admin",
        "email": "system@lxai.com",
        "full_name": "系统管理员",
        "hashed_password": "$2b$12$w8GM49ePhxbCzT6qWNnvHOx/VHCh0MOmbFjUpFUG8Y4OTDmeM0Iq.",
        "role": "admin",
        "is_verified": True,
        "is_active": True,
    },
    {
        "id": 2,
        "username": "demo_user",
        "email": "demo@lxai.com",
        "full_name": "演示用户",
        "hashed_password": "$2b$12$w8GM49ePhxbCzT6qWNnvHOx/VHCh0MOmbFjUpFUG8Y4OTDmeM0Iq.",
        "role": "user",
        "is_verified": True,
        "is_active": True,
    },
]
