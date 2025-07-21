# Demo Accounts

The following demo accounts are available for testing:

## Account 1
- **Email**: `demo@example.com`
- **Password**: `demopassword123`
- **Role**: Admin in Demo Organization

## Account 2 (Simpler password)
- **Email**: `demo2@example.com`
- **Password**: `demo123`
- **Role**: Admin in Demo Organization

## Frontend Access
1. Open http://localhost:3001
2. Use either demo account to login
3. The app will automatically handle the multi-tenant authentication

## API Access
The API is running at http://localhost:8000/api/v2

### Login via API:
```bash
curl -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo2@example.com","password":"demo123"}'
```

### API Documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc