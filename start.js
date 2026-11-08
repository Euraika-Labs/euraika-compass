// Capture/local.set pattern from the Pinokio server example and current guide.
module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        path: "app/backend",
        conda: { path: "../runtime", python: "3.12" },
        venv: "env",
        message: "python ../scripts/manage.py serve --port {{port}}",
        on: [{ event: "/(http:\/\/[0-9.:]+)/", done: true }],
      },
    },
    { method: "local.set", params: { url: "{{input.event[1]}}" } },
  ],
};
