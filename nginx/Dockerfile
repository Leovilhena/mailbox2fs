FROM alpine:3

LABEL maintainer="Leonardo Silva Vilhena <leosvilhena@icloud.com>"

RUN set -x \
    && apk update \
    && apk upgrade \
    && apk add --no-cache \
    g++ \
    openssl-dev \
    zlib-dev \
    libxslt-dev \
    geoip-dev \
    make

RUN set -x \
    && addgroup -g 101 -S nginx \
    && adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx

COPY --chown=nginx:nginx repositories/nginx /nginx
COPY --chown=nginx:nginx repositories/nginx-dav-ext-module /nginx/nginx-dav-ext-module

WORKDIR nginx

RUN set -x \
    && /nginx/auto/configure --prefix=/opt/nginx \
    --with-compat \
    --with-http_addition_module \
    --with-http_auth_request_module \
    --with-http_dav_module \
    --with-http_degradation_module \
    --with-http_flv_module \
    --with-http_geoip_module \
    --with-http_gunzip_module \
    --with-http_gzip_static_module \
    --with-http_mp4_module \
    --with-http_realip_module \
    --with-http_secure_link_module \
    --with-http_slice_module \
    --with-http_ssl_module \
    --with-http_stub_status_module \
    --with-http_sub_module \
    --with-http_v2_module \
    --with-pcre-jit \
    --with-threads \
    --without-http_rewrite_module \
    --without-http_geo_module \
    --add-module=nginx-dav-ext-module

RUN set -x \
    && make \
    && make install

RUN set -x \
    && ln -sf /dev/stdout /opt/nginx/logs/access.log \
    && ln -sf /dev/stderr /opt/nginx/logs/error.log \
    && mkdir /docker-entrypoint.d

RUN set -x \
    && apk del \
    g++ \
    make

COPY config/nginx.conf /opt/nginx/conf/nginx.conf
COPY --chown=nginx:nginx scripts/docker-entrypoint.sh /

RUN chmod +x /docker-entrypoint.sh
RUN chown -R nginx:nginx /opt/nginx/

USER nginx:nginx

ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 8080

STOPSIGNAL SIGTERM

CMD ["/opt/nginx/sbin/nginx", "-g", "daemon off;"]