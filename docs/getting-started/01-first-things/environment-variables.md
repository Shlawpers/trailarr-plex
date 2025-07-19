**Environment variables are OPTIONAL.**

Here are the optional environment variables you can set:

### `APP_DATA_DIR`

- Default is `/config`.

This environment variable is used to set the application data directory. If setting this, make sure to map the volume to the same directory.

Useful if you want to store the application data in a different directory than the default.

For example, if you want to store the application data in `/app_config/abc`, you can set the `APP_DATA_DIR` environment variable like this:

```yaml hl_lines="2 4"
    environment:
        - APP_DATA_DIR=/app_config/abc
    volumes:
        - /var/appdata/trailarr:/app_config/abc
```

!!! warning
    If you are setting the `APP_DATA_DIR` environment variable, make sure to set an absolute path like `/data` or `/config/abc`, and map the volume to the same directory.

!!! danger
    Do not set `APP_DATA_DIR` to `/app` or `/tmp` or any other linux system directory. This could cause the application to not work correctly or data loss.


### `PGID`

- Default is `1000`.

This environment variable is used to set the group ID for the application.

Useful if you have permission issues with the application writing to the volume. You can set the group ID to the group of the volume or a group that has read/write permissions to the volume.

```yaml
    environment:
        - PGID=1000
```


### `PUID`

- Default is `1000`.

This environment variable is used to set the user ID for the application.

Useful if you have permission issues with the application writing to the volume. You can set the user ID to the owner of the volume or a user that has read/write permissions to the volume.

```yaml
    environment:
        - PUID=1000
```


### `TZ`

- Default is `America/New_York`.

This environment variable is used to set the timezone for the application.

For a list of valid timezones, see [tz database time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

```yaml
    environment:
        - TZ=America/New_York
```

### `WEBUI_DISABLE_AUTH`

- Default is `False`.

This environment variable is used to disable the authentication for the web interface.
    
```yaml
    environment:
        - WEBUI_DISABLE_AUTH=True # This will disable the web UI authentication
```

### `WEBUI_PASSWORD`

- Default is `trailarr` (hashed).

Trailarr Web Interface has a browser login to access the app. Default credentials are:

```bash
Username: admin
Password: trailarr
```

If you forget your password, set this environment variable to `''` (empty string) to reset the password for the web interface to default.

```yaml
    environment:
        - WEBUI_PASSWORD='' # This will reset the password to default
```

To change the password, go to `Settings > About > Password` in web interface. 

!!! info
    If you change your password from the web interface, the password will be hashed and stored internally. There is no way to retrieve the password as only a hashed version is stored, you need to reset it if you forget it.

!!! warning
    Once you change your password, don't forget to remove the `WEBUI_PASSWORD` environment variable from the docker-compose file.

### `PLEX_URL`

- Default is `http://plex:32400`.

URL for your Plex server. This is only required if you want Trailarr to check Plex for existing trailers.

```yaml
    environment:
        - PLEX_URL=http://localhost:32400
```

### `PLEX_TOKEN`

- **Required** when `RESPECT_PLEX_PASS_TRAILERS` is `true`.

Authentication token for your Plex server.

```yaml
    environment:
        - PLEX_TOKEN=abc123
```

### `RESPECT_PLEX_PASS_TRAILERS`

- Default is `false`.

When set to `true`, Trailarr checks Plex for an existing trailer before every
download attempt. If Plex already provides a trailer (type `clip` and subtype
`trailer`), Trailarr logs `"Skipped trailer download for [title] - Plex Pass already provides trailer."`
and does not download or replace the trailer.
You can toggle this option from the UI under **Settings > General > Respect Plex Pass**, but a container restart is required for the change to take effect.

```yaml
    environment:
        - RESPECT_PLEX_PASS_TRAILERS=true
```


### Example

Here is an example of setting the environment variables:

```yaml
    environment:
        - TZ=America/Los_Angeles
        - PUID=1000
        - PGID=1000
        - APP_DATA_DIR=/data/trailarr
    volumes:
        - /var/appdata/trailarr:/data/trailarr
```

This sets the environment variables to run the app with following settings:

- Timezone: America/Los_Angeles
- User ID: 1000
- Group ID: 1000
- Application data directory: /data/trailarr
- Volume mapping: /var/appdata/trailarr:/data/trailarr

