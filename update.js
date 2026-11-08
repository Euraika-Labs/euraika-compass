module.exports = {
  run: [
    {
      when: "{{!running('start.js')}}",
      method: "shell.run",
      params: { message: "git pull --ff-only" },
    },
    {
      when: "{{!running('start.js')}}",
      method: "script.start",
      params: { uri: "install.js" },
    },
  ],
};
