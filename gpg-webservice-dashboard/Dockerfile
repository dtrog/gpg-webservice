FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx configuration template
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy config template
COPY config.template.js /etc/config.template.js

# Copy static files
COPY index.html /usr/share/nginx/html/
COPY register.html /usr/share/nginx/html/
COPY login.html /usr/share/nginx/html/
COPY profile.html /usr/share/nginx/html/
COPY debug.html /usr/share/nginx/html/
COPY admin.html /usr/share/nginx/html/
COPY admin-login.html /usr/share/nginx/html/
COPY disclaimer.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Expose port 80 (default) or PORT env var
EXPOSE 80

# Start nginx with envsubst for PORT and API_URL variables
CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && envsubst '${API_URL}' < /etc/config.template.js > /usr/share/nginx/html/js/config.js && nginx -g 'daemon off;'"]
