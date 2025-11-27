FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy nginx configuration template
COPY gpg-webservice-dashboard/nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy config template
COPY gpg-webservice-dashboard/config.template.js /etc/config.template.js

# Copy static files
COPY gpg-webservice-dashboard/index.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/register.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/login.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/profile.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/debug.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/admin.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/admin-login.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/disclaimer.html /usr/share/nginx/html/
COPY gpg-webservice-dashboard/css/ /usr/share/nginx/html/css/
COPY gpg-webservice-dashboard/js/ /usr/share/nginx/html/js/

# Expose port 80 (default) or PORT env var
EXPOSE 80

# Start nginx with envsubst for PORT and API_URL variables
CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && envsubst '${API_URL}' < /etc/config.template.js > /usr/share/nginx/html/js/config.js && nginx -g 'daemon off;'"]
