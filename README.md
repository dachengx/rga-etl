# RGA-ETL

Extract, transform, and load the data from an SRS RGA200.

## srsinst.rga

The repo is based on the python wrapped interface for RGA communication. Reference: [srsinst.rga](https://github.com/thinkSRS/srsinst.rga).

## MySQL Database

On macOS, install docker-desktop by

```
brew install --cask docker
```

-----

Initialize a MySQL server inside a container and put it in the background:

```
open -a Docker
docker compose up -d
```

The configuration is at `docker-compose.yml`.

Use `docker stats` to check the status of the container. Use `docker ps --all` to check all containers including those closed. 

-----

Connect to the MySQL container with username `root`:

```
docker exec -it rga-mysql mysql -uroot -p
```

-----

Install MySQL related python packages:

```
pip install sqlalchemy dotenv
```
