# Taskmaster

## Subject

Example of what to do is [supervisor](http://supervisord.org)

### Description
- The program will not run as root
- It must provide a control shell to the user

### Authorizations
- Any programming language
- Libraries can be used to parse configuration files
- Libraries can be used to make the "client/server" bonus
- All of the standard library is authorized

### Correction
- Must be run in a virtual machine (any tools are alowed to set it up)
- Demonstrate that every features works
    - Manual killing of processes
    - Start processes that don't work
    - Start processes that generate lots of output
- We must provide at least one configuration file

### Required features
- Make an author files :eyes:
- Must keep child processes alive by restarting them (if required)
- Must know at all times the state of monitored processes (alive/dead)
- Have a configuration file (ex: YAML)
    - Configuring a process
        - Start command
        - Number of process to start and keep alive
        - If program is started at launch or not
        - If program should restart
            - always
            - never
            - on unexpected exits
        - What return code are "unexpected exists"
        - How long a program should run for to be considered "successfully started"
        - How many restart should be attempted before aborting
        - Which signals should be used for a gracefull shutdown
        - How long to wait for a gracefull shutdown before killing it
        - Optional redirections of stdout/stderr files
        - Environment variables
        - The working directory
        - The umask used by the program
    - That can be hot reloaded on SIGHUP
        - Then stear process pool to correct state
            - Kill *unnecessary* processes
            - Start newly required programs
- Have logging system outputing to local file
    - Program start
    - Program stop
    - Program restart
    - Unexpected program failure
    - Configuration reload
- Stay in foreground a have control shell
    - Line editing
    - History
    - Completion (optional)
- The shell must have the following features
    - See every program's status
    - Start / stop / restart a program
    - Hot reload the configuration file
    - Stop the main program

### Bonus features
- Anything useful to the project, including
- Priviledge de-escalation at launch
- Client/server architecture, a deamon & a control program
- More advanced logging/reporting (alerts via email/http/syslog/etc..)
- Allow to attach & detach a supervised process to console (like tmux & screen)

### Advices
Try out supervisor, and when in doubt on a behaviour do as it does

### Configuratoin file example

```yaml
programs:
    nginx:
    cmd: "/usr/local/bin/nginx -c /etc/nginx/test.conf"
    numprocs: 1
    umask: 022
    workingdir: /tmp
    autostart: true
    autorestart: unexpected
    exitcodes:
        - 0
        - 2
    startretries: 3
    starttime: 5
    stopsignal: TERM
    stoptime: 10
    stdout: /tmp/nginx.stdout
    stderr: /tmp/nginx.stderr
    env:

vogsphere:
    cmd: "/usr/local/bin/vogsphere-worker --no-prefork"
    numprocs: 8
    umask: 077
    workingdir: /tmp
    autostart: true
    autorestart: unexpected
    exitcodes: 0
    startretries: 3
    starttime: 5
    stopsignal: USR1
    stoptime: 10
    stdout: /tmp/vgsworker.stdout
    stderr: /tmp/vgsworker.stderr
```
