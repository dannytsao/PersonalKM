# PersonalKM Agent Instructions

## Deployment

After completing code or configuration changes in this repository:

1. Run the relevant tests or checks for the changed area.
2. Commit the finished changes on `main`.
3. Push to `origin main`.
4. Confirm the Render service is live by checking:

   `https://personal-km-line-bot.onrender.com/health`

The Render web service is configured with `autoDeploy: true`, so pushing to `main` triggers deployment automatically.

If the push is rejected because remote `main` contains new bot-generated note commits, run `git pull --rebase origin main`, rerun relevant tests, then push again.
