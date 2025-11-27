FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx configuration template
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy static files
COPY index.html /usr/share/nginx/html/
COPY register.html /usr/share/nginx/html/
COPY login.html /usr/share/nginx/html/
COPY profile.html /usr/share/nginx/html/
COPY debug.html /usr/share/nginx/html/
COPY admin.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Expose port 80 (default) or PORT env var
EXPOSE 80

# Start nginx with envsubst for PORT variable
CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
