# Cliente do CARLA 0.9.6. A biblioteca do CARLA só existe para Python 3.6.
# Ubuntu 18.04 traz o Python 3.6.9 e as bibliotecas que ela precisa (libjpeg8, libpng16 e libtiff5).
FROM ubuntu:18.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-numpy python3-setuptools libpng16-16 libjpeg8 libtiff5 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 LANG=C.UTF-8
WORKDIR /app

CMD ["python3", "-m", "carla_client.run"]
