// Only generated dependencies under this checkout; never data or model directories.
module.exports = {
  run: [
    { when: "{{!running('start.js')}}", method: "fs.rm", params: { path: "app/backend/env" } },
    { when: "{{!running('start.js')}}", method: "fs.rm", params: { path: "app/frontend/node_modules" } },
    { when: "{{!running('start.js')}}", method: "fs.rm", params: { path: "app/frontend/dist" } },
  ],
};
