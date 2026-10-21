/**
 * Node filesystem shim implementing the narrow surface workflow.js needs.
 *
 * @module dsh-trellis/node-fs
 */
import {
  stat as nodeStat,
  readFile as nodeReadFile,
  writeFile as nodeWriteFile,
  rename as nodeRename,
  mkdir as nodeMkdir,
  rmdir as nodeRmdir,
  unlink as nodeUnlink,
} from "node:fs/promises";

/** @type {import("./workflow.js").FsShim} */
export const nodeFs = {
  async exists(path) {
    try {
      await nodeStat(path);
      return true;
    } catch {
      return false;
    }
  },
  async stat(path) {
    try {
      const info = await nodeStat(path);
      return { mtimeMs: info.mtimeMs, isDirectory: info.isDirectory() };
    } catch {
      return null;
    }
  },
  async readFile(path) {
    try {
      return await nodeReadFile(path, "utf8");
    } catch {
      return null;
    }
  },
  // Write surface used by the one-time project-config migration. Read-only
  // callers never touch these, and test shims that omit them are detected by
  // the writer instead of failing halfway.
  async writeFile(path, content, options) {
    await nodeWriteFile(path, content, options);
  },
  async rename(from, to) {
    await nodeRename(from, to);
  },
  async mkdir(path, options) {
    await nodeMkdir(path, options);
  },
  async rmdir(path) {
    await nodeRmdir(path);
  },
  async unlink(path) {
    await nodeUnlink(path);
  },
};
