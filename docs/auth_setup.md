# 🔐 Authentication Setup

## Default Users
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Full access |
| manager | manager123 | Read + Write |
| viewer | viewer123 | Read only |

## API Usage
1. Login: POST /api/v1/auth/login?username=admin&password=admin123
2. Use token: Authorization: Bearer <token>
3. Check current user: GET /api/v1/auth/me

## Role Permissions
- admin: read, write, delete, manage_users
- manager: read, write
- viewer: read only

## Change JWT Secret
Set JWT_SECRET in .env file.
