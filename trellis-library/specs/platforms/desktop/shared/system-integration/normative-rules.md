# Normative Rules

* Desktop features that depend on OS services must keep the integration boundary
  explicit so application behavior is not designed around hidden platform magic.
* Native dialogs, filesystem picks, notifications, deep links, or shell actions
  should fail predictably when the platform denies access, the capability is
  unavailable, or user input is cancelled.
* OS-provided paths, permissions, and capability handles must not be treated as
  universally stable across development, packaging, and user environments.
* Application code should preserve a clear boundary between app-owned logic and
  system-integration adapters so platform-specific behavior remains diagnosable.
* User-visible desktop integrations should stay understandable enough that
  support, debugging, and recovery do not depend on hidden environment state.
