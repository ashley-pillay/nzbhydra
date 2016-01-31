# NZB Hydra changelog

----------
### 0.0.1a59
Completely rewrote duplicate detection. Fixes an ugly bug, should take 2/3 of the time and easier to fix or expand in the future.
 
Added argument switches for PID file and log file location.
 
When an indexer wasn't searched (e.g. because it doesn't support any of the search types) a message will be shown and the search is not considered unsuccessful.

Use proper caching so that the assets should only be reloaded when they've actually changed (and then actually reload). Should make page loading faster on slow upstream servers and solve problems with outdated assets.

Movde about, updates, log and control sections to their own "System" tab (like sonar ;-)).

### 0.0.1a58
Still getting used to writing the change log so I might often forget it for a while.

Fixed a bug where duplicate detection would ironically cause duplicates which caused some weird bugs in the system. Was a pain in the ass to debug and fix.

Added an option to look at this (the changelog) before updating. Will also add a changelog in the about section with the latest changes already included in the running version.

Removed "direct" NZB access type. Programs will always need to contact NZB Hydra to get their NZBs.

### 0.0.1a57
First version with changelog

### 0.0.1a56
Last version without changelog