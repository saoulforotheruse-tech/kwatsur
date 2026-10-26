FROM nginx:1.27-alpine

COPY public /usr/share/nginx/html
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

# Seules les variables listées ici sont remplacées dans le gabarit (pas $uri, $host…).
ENV NGINX_ENVSUBST_FILTER=KWATSUR_
ENV KWATSUR_API_URL=http://host.docker.internal:8000

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
