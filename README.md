# 설치

설치를 위해선 Docker, docker-compose가 필요.

다음 두 커맨드를 실행하여 첫 빌드를 수행.
```shell
docker-compose build
docker-compose run --rm backend python -m image_hub.database.commands.create_db_schema
```

다음 커맨드를 실행하여 어플리케이션을 실행시킨다.
```shell
docker-compose up
```

이후는 다시 빌드만이 필요하면 docker-compose 빌드 커맨드를 사용.
```shell
docker-compose build
```

# 어드민 유저 추가

아래 커맨드에서 `{유저 이름}`과 `{패스워드}`를 원하는 유저 이름과 패스워드로 교체해서 커맨드를 실행.
```shell
docker-compose run --rm backend python -m image_hub.auth.commands.create_admin --name={유저 이름} --password={패스워드}
```

# DB Schema 삭제와 제 생성
PostgreSQL을 사용하기 때문에 [image_hub/database/models.py](image_hub/database/models.py)에 존재하는 ORM 클래스를 수정한다면,
DB Schema를 지우고 다시 생성할 필요가 있음.

### Schema 생성 스크립트
[create_db_schema.py](image_hub/database/commands/create_db_schema.py)

docker-compose를 사용해 실행.
```shell
docker-compose build
docker-compose run --rm backend python -m image_hubF.database.commands.create_db_schema
```

### DB 삭제 스크립트
[delete_db_schema.py](image_hub/database/commands/delete_db_schema.py)

docker-compose를 사용해 실행.
```shell
docker-compose build
docker-compose run --rm backend python -m image_hub.database.commands.delete_db_schema
```

