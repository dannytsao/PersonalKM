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

## End-of-Day Trigger

When the user says `call it a day` (or similar), run the end-of-day wrap-up workflow **before closing**:

1. **Sync both repos** with `origin/main`:
   ```bash
   cd ~/Documents/PersonalKM && git pull --rebase origin main
   cd ~/.personalkm/PersonalKM-worker && git pull --rebase origin main
   ```
2. **Update all project docs** that changed during the session:
   - `CHANGELOG.md` — add entry for the day with all meaningful changes (features, fixes, architecture)
   - `README.md` — update `Last Updated:` date; add brief note if a major feature landed
   - `DESIGN.md` — update `最後更新:` date if architecture or flow changed
   - `DOCS-INVENTORY.md` — update `更新日期:` if doc structure changed
   - Any other doc that is now inaccurate
3. **Run `git diff --check`** to catch trailing whitespace or merge conflicts.
4. **Commit** with message: `docs: end-of-day wrap-up YYYY-MM-DD`
5. **Push** to `origin main`.
6. **Sync vault** (worker repo pulls the same commit).
7. **Confirm** local `HEAD` matches `origin/main` in both repos and Render health endpoint is live.

> All docs live in the same GitHub repo as the vault. A single push updates both the source code repo and the knowledge vault simultaneously.
