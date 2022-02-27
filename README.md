
# Custom history API for Train of the Century

This project serves as a backbone for different features in the "Train of the Century" game on the WAX blockchain.
You can also run this API locally for your own needs or host it publicly to provide it as a service for others.

## Install

If you already have docker and docker-compose installed you can simply clone this repositoy and then run the init script:

```sh
$ git clone https://github.com/automaqqt/toc-history-api.git && cd toc-history-api
$ bash init.sh
```

If you dont have docker installed and run Ubuntu 20.04 you can use the full init bash script:

```sh
$ git clone https://github.com/automaqqt/toc-history-api.git && cd toc-history-api
$ bash init_full_ubuntu.sh
```

Congrats! You can now reach your own instance of the ToC history API: [local docs](http://localhost:8001/docs)


## Restart or Update

Run docker-compose to restart the service:

```sh
$ docker-compose up -d --build
```

## Migrate database changes

In case of changes to the SQL models you gonna have to run a migration on your local database:

```sh
$ bash migrate.sh
```

## Issues and Contributions

You experience any issue or found a bug? Please open a issue report within this repository!

You want to contribute to this repository? Open a PR with a little explanation and it gonna be reviewed asap. Thanks for helping out :)