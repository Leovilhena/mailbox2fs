# Exposing Mailbox as a Filesystem 

This is the version development version for the task found at mailbox2f file.
There goal is to create a synthetic (pseudo) filesystem from your mailbox in read-only mode accessed via WebDav with NGINX.


How to run:

```bash
./run.sh
```
- You'll be prompt for username and password (not echoed to the terminal) regarding Fastmail.
- There are more environment variables available to be set if needed (ex.: Other mail services). Please check the main.py script.


How to set App passwords: 

https://www.fastmail.com/help/clients/apppassword.html?u=9e2140d7


Considerations:

- This is a development version which still lacks some security features.
- The NGINX latest version was not working with WebDav, so I had to build it from the source code with WebDav and
WebDav extension module. Both repositories were downloaded and saved into nginx/repositories folder as git submodules.
- This new NGINX Dockerfile was based on the original one with a few changes.


 