# Nebula Ubuntu Setup Guide

Welcome to Nebula! This guide will help you spin up the Nebula backend platform on an Ubuntu server and configure it for Meta's WhatsApp API.

## Prerequisites

1. An Ubuntu Server (20.04 or 22.04 recommended).
2. Root or `sudo` access.
3. A registered domain name (optional but highly recommended for Meta Webhooks, which require HTTPS).
4. A Meta Developer Account (for WhatsApp API).

---

## 1. Install Docker & Docker Compose

First, make sure your system packages are up to date and install Docker.

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group so you don't have to use 'sudo' every time
sudo usermod -aG docker $USER
```
*(You may need to log out and log back in for the group change to take effect).*

---

## 2. Clone the Repository and Setup Environment Variables

Clone the Nebula codebase to your server:

```bash
# Clone the repository
git clone <YOUR_GITHUB_REPO_URL_HERE> nebula
cd nebula

# Copy the sample environment file
cp .env.sample .env
```

**Edit your `.env` file:**
Use `nano .env` to open the file and configure the following required fields:
- `SECRET_KEY`: Generate a secure random string (e.g. run `openssl rand -hex 32`)
- `ENVIRONMENT`: Set to `production`
- `POSTGRES_PASSWORD`: Change this to a secure database password
- `WHATSAPP_APP_SECRET`: (We will get this in Step 4)
- `WHATSAPP_VERIFY_TOKEN`: Set this to a random string of your choice (you will provide this same string to Meta later)

---

## 3. Start the Platform

With Docker installed and `.env` configured, you can launch the entire stack (API, Background Worker, PostgreSQL, Redis, and Qdrant) with one command.

For production, we will use the production compose override file which runs Gunicorn and removes local volume mounts:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

To verify everything is running smoothly:
```bash
docker compose ps
```

Your API is now running locally on port `8000`. You will need to expose this port to the public internet using a reverse proxy like **Nginx** or **Caddy** and secure it with SSL/TLS (Meta webhooks strictly require `https://`).

---

## 4. Setting up the WhatsApp Bot (Meta Developer Portal)

To connect Nebula to WhatsApp, follow these steps on the [Meta Developer Portal](https://developers.facebook.com/):

### A. Create the App
1. Go to **My Apps** -> **Create App**.
2. Select **Other** -> **Business** -> Fill in app details.
3. Once created, scroll down and add the **WhatsApp** product.

### B. Configure Webhooks
1. In the left menu under WhatsApp, click **Configuration**.
2. Under the Webhooks section, click **Edit**.
3. **Callback URL**: `https://<YOUR_DOMAIN>/api/v1/webhooks/whatsapp`
   > **💡 Tip for Local Testing:** Meta requires a public HTTPS URL. If you are testing locally on your laptop, you cannot use `http://localhost`. Instead, use a tunneling service like [ngrok](https://ngrok.com/). Run `ngrok http 8000` in a new terminal, and use the provided HTTPS URL here (e.g., `https://a1b2c3d4.ngrok-free.app/api/v1/webhooks/whatsapp`).
4. **Verify Token**: Enter the exact string you placed in `WHATSAPP_VERIFY_TOKEN` in your `.env` file.
5. Click **Verify and Save**. (If Nebula is running and exposed correctly, Meta will send a challenge request and Nebula will automatically respond and verify it).

### C. Subscribe to Webhook Fields
Once the webhook is verified, click **Manage** next to Webhook fields. Subscribe to:
- `messages` (to receive incoming messages from customers)
- `messages_status` (optional, for read/delivered receipts)

### D. Get API Credentials
1. In the Meta Dashboard, go to **App Settings** -> **Basic**.
2. Click **Show** next to **App Secret**. Copy this and paste it into `WHATSAPP_APP_SECRET` in your `.env` file. (This is required for payload signature verification to prevent spoofing).
3. Under **WhatsApp** -> **API Setup**, you will find your **Temporary Access Token** (or you can generate a permanent one via System Users).
4. You will also see your **Phone Number ID** and **WhatsApp Business Account ID**.

### E. Register the Business in Nebula
Finally, to link this WhatsApp number to a specific Business tenant in Nebula, use the Nebula API (via Postman, cURL, or the Swagger UI at `http://<YOUR_DOMAIN>/docs`):

1. **Create an Integration Record:**
   Make a `POST` request to `/api/v1/integrations/` to register your WhatsApp credentials for your tenant.
2. Nebula will now automatically handle incoming messages from your WhatsApp number, route them to the conversation engine, and use the LLM to reply!
