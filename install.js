module.exports = {
  requires: { bundle: "ai" },
  run: [
    {
      method: "shell.run",
      params: {
        path: "app",
        conda: { path: "runtime", python: "3.12" },
        message: "conda install -y -p runtime -c conda-forge python=3.12 postgresql=16.15 pgvector=0.8.6",
      },
    },
    {
      method: "shell.run",
      params: {
        path: "app/backend",
        conda: { path: "../runtime", python: "3.12" },
        venv: "env",
        message: ["uv pip install -r requirements-dev.lock", "uv pip install --no-deps -e ."],
      },
    },
    {
      method: "shell.run",
      params: {
        path: "app/frontend",
        message: ["npm ci", "npm run build"],
      },
    },
    {
      method: "shell.run",
      params: {
        path: "app/backend",
        conda: { path: "../runtime", python: "3.12" },
        venv: "env",
        message: "python ../scripts/manage.py doctor",
      },
    },
  ],
};
