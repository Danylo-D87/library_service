# Library Management API

This project is a backend service for managing a library system. It includes functionalities for user management, book catalog, borrowing system, and payment handling via Stripe. The API is built with Django REST Framework and provides OpenAPI schema with Swagger and Redoc documentation.

---

## Features

* **User Management**

  * User registration and profile management with JWT authentication.
  * Staff user permissions for sensitive operations.

* **Books Management**

  * CRUD operations on books with inventory tracking.
  * Public access for safe (read-only) methods; staff permissions for modifications.

* **Borrowings**

  * Users can borrow books, with inventory decrement upon borrowing.
  * Borrowing status tracking and return functionality with fine calculation.
  * Filtering borrowings by active status and user (staff only).

* **Payments**

  * Integration with Stripe for borrowing fees and fines.
  * Stripe webhook handling for payment confirmation, cancellation, and inventory adjustments.
  * Async notifications via Telegram on payment events.

* **API Documentation**

  * Auto-generated OpenAPI schema with Swagger UI and Redoc accessible via `/api/docs/swagger/` and `/api/docs/redoc/`.

---

## Project Structure

* **config** — project settings, main URL routing, and Celery integration.
* **users** — user models, serializers, views, and authentication.
* **books** — book-related models, serializers, and API endpoints.
* **borrowings** — borrowing logic, status management, and payment initiation.
* **payments** — payment models, webhook processing, and Stripe session management.
* **config/notifications/tasks.py** — asynchronous Telegram notification tasks powered by Celery.

---

## Getting Started with Docker

### 1. Clone the repository

```bash
git clone <repository_url>
cd <repository_folder>
```

### 2. Environment variables

Create a `.env` file in the root directory with at least the following variables:

```
SECRET_KEY=your_django_secret_key
DEBUG=1
DATABASE_URL=postgres://user:password@db:5432/library_db
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
REDIS_URL=redis://redis:6379/0
```

### 3. Build and run containers

```bash
docker compose build
docker compose up -d
```

This will start containers for:

* Django API server
* PostgreSQL database
* Redis (for Celery backend)
* Celery worker and beat scheduler

### 4. Apply migrations and create superuser

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### 5. Access API

* Swagger UI: `http://localhost:8000/api/docs/swagger/`
* Redoc: `http://localhost:8000/api/docs/redoc/`
* Admin panel: `http://localhost:8000/admin/`

---

## Notes

* Celery tasks handle Telegram notifications asynchronously to avoid blocking request/response cycles.
* Payment flow uses Stripe checkout sessions; webhook endpoint processes payment status updates.
* Proper permission checks are enforced: staff users have elevated rights, regular users have limited access.
* Inventory is adjusted automatically on borrowing creation and return events, with rollback on payment failures or cancellations.

---