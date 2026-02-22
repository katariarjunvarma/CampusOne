# Email Setup for CampusOne

This guide will help you configure Gmail SMTP for sending real email notifications to students when they are marked absent.

## Step 1: Enable 2-Factor Authentication (2FA) on Gmail

1. Go to [myaccount.google.com](https://myaccount.google.com/)
2. Click on **Security** in the left sidebar
3. Scroll down to **Signing in to Google** section
4. Click on **2-Step Verification** (if not already enabled)
5. Click **Get Started** and follow the setup process
6. You'll need to:
   - Enter your phone number
   - Verify with a code sent to your phone
   - Enable 2FA

## Step 2: Generate an App Password

After enabling 2FA, you need to create an App Password for CampusOne:

1. Go back to [myaccount.google.com/security](https://myaccount.google.com/security)
2. In the **Signing in to Google** section, click on **App passwords**
3. You may need to sign in again
4. Under **Select app**, choose **Other (Custom name)**
5. Enter "CampusOne" as the app name
6. Click **Generate**
7. Copy the 16-character password (it will look like: `xxxx xxxx xxxx xxxx`)
8. **Important**: Save this password securely. You won't see it again.

## Step 3: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your actual credentials:
   ```bash
   nano .env
   # or use any text editor
   ```

3. Replace the placeholder values:
   ```env
   # Your Gmail address
   EMAIL_HOST_USER=your-actual-email@gmail.com
   
   # The 16-character app password you generated (remove spaces)
   EMAIL_HOST_PASSWORD=xxxxxxxxxxxxxxxx
   
   # Optional: Custom from email
   DEFAULT_FROM_EMAIL=CampusOne <your-actual-email@gmail.com>
   ```

4. Save the file and exit the editor

## Step 4: Install Dependencies

Make sure you have `python-dotenv` installed:

```bash
pip install python-dotenv
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

## Step 5: Test the Configuration

1. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

2. Log in to CampusOne and mark a student as absent

3. Check if:
   - The student receives a real email at their registered email address
   - No error messages appear in the console

## Troubleshooting

### Emails not sending?
- Check that your Gmail has 2FA enabled
- Verify the app password is correct (no spaces)
- Make sure the `.env` file is in the project root
- Check Django console for error messages

### Authentication failed error?
- Generate a new app password (they expire after use sometimes)
- Ensure you're using the app password, NOT your regular Gmail password
- Check that the email address is exactly correct

### Still using console backend?
- Verify that both `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set in `.env`
- Restart the Django server after changing `.env` file
- Check that there are no typos in variable names

## Security Notes

- **Never commit your `.env` file to Git** - it's already in `.gitignore`
- The app password gives access to your Gmail account - keep it secure
- Consider creating a dedicated Gmail account for the application
- Regularly rotate your app passwords for better security

## Running in Production

For production deployment, consider:
- Using a transactional email service (SendGrid, Mailgun, etc.)
- Setting up proper domain authentication (SPF, DKIM, DMARC)
- Using environment-specific configuration files
- Implementing email queueing for better performance
