This (docker) service can be installed on your media server (emby, plex, ...). It will automatically translate subtitle files. Currently only SRT files are supported. It uses DeepL for translating. Note that DeepL is not fully free.

Setup:
- Create account at https://www.deepl.com and request your API token/key (first try for free, then upgrade to Pro if happy) 
- Install docker and docker-compose if not already installed
- Fill environment variables in the docker-compose.yml
- TARGET_LANG shall be the target language to translate the subtitles (see Deepl API docs for all available languages and their abbreviations)
- WATCH_DIR shall be the directory where to recursively check for SRT or ASS files which were not yet translated to the TARGET_LANG
- DEEPL_API_KEY the received API token/key
- SLEEP_INTERVAL the interval in which to check for new subtitle files
- Run docker-compose up -d to start the service
