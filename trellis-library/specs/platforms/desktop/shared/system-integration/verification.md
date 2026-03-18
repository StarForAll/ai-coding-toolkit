# Verification

Check the following:

* system-integration boundaries are explicit in the design
* cancellation, denial, or unavailability of OS services degrades predictably
* local paths, permission state, and capability handles are not overgeneralized
* app-owned logic remains separated from OS adapter code
* user-visible recovery or support paths remain understandable
