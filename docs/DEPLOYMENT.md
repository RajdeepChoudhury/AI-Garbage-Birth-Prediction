# Installation and deployment

## Requirements

Python 3.12, Node 22, and optionally Docker with Compose. A Groq API key is only needed for the assistant.

## Installation

See the quick start and local development sections in the main README. In short: train the models in `ml`, run the backend in `backend`, run the frontend in `frontend`.

## Docker Compose

The compose file defines PostgreSQL, Redis, the backend, the frontend (nginx on port 8080), and a one off `trainer` job.

1. Copy `.env.example` to `.env` and replace every value marked CHANGE.
2. Create the models: `docker compose --profile train run --rm trainer`
3. Start the stack: `docker compose up --build -d`
4. Check health: `curl http://localhost:8000/health` should show `model_loaded` as true.

The backend reads models from the `ml` folder, mounted read only. Retrain and restart the backend to use new models.

The frontend gets its API address at build time through `VITE_API_URL`. Set it to the public address of your backend, and add the frontend's address to `CORS_ORIGINS`.

This setup has not been run in the environment where it was written, so expect to fix small issues on first start.

## Production checklist

* Set a long random `SECRET_KEY`. The app refuses to start in production without one.
* Use strong database and admin passwords, and serve everything over HTTPS.
* Add Alembic migrations before changing the schema. Until then keep one backend worker.
* Replace `OVERFLOW_CAPACITY` with real capacities, and review the heuristics in the Models document.
* Move tokens from local storage to secure cookies, and review CORS origins.
* Back up the PostgreSQL volume.

## Hosting platforms

Any platform that runs containers can host this. The general shape is the same everywhere: one managed PostgreSQL database, one Redis instance, the backend image with the environment variables above, the frontend as static files or the nginx image, and a way to supply the trained model files to the backend (a mounted volume, or bake them into the image in your own build). The Render, Railway, Netlify, Vercel, AWS and Azure setups from the original brief are not written or tested here.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request. It generates data and trains models, runs the backend tests, runs the frontend tests and build, then builds both Docker images. Model files are generated in CI because they are not stored in Git.
