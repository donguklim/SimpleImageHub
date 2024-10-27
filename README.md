## 설치

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

## 어드민 유저 추가

아래 커맨드에서 `{유저 이름}`과 `{패스워드}`를 원하는 유저 이름과 패스워드로 교체해서 커맨드를 실행.
```shell
docker-compose run --rm backend python -m image_hub.auth.commands.create_admin --name={유저 이름} --password={패스워드}
```

## DB Schema 삭제와 제 생성
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

## 샘플 데이터 추가

```shell
docker-compose run --rm backend python -m image_hub.commands.create_sample_data
```

- `admin1`, `admin2`, ... `admin10` 아이디의 어드민 계정 10개를 생성함.

- `user1`, `user2`, ... `user10` 아이디의 일반 유저 계정 10개를 생성함.

- `CATEGORY_1`, `CATEGORY_2`, ... `CATEGORY_50`라는 이름의 50개의 카테고리를 생성함.

- 모든 유저의 패스워드는 `asdf`로 세팅되어 있고, 각 유저별로 해당 랜덤한 개수의 랜덤 이미지를 생성한다. (최소 1개)

## API 문서

`http://localhost:8000/docs` 주소에 Swagger 페이지가 있습니다.


## DB Schema

[ERD 파일](resources/db_schema.pgerd)
![](resources/image_hub_erd.png "Title")
