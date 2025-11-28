FROM nginx:alpine

# Copy static nginx configuration (no runtime substitution needed)
COPY nginx.conf.static /etc/nginx/conf.d/default.conf

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

# Create a template for config.js with API_URL placeholder
RUN echo 'window.CONFIG = { API_URL: "${API_URL}" };' > /etc/config.template.js

# Set default environment variable
ENV API_URL=http://localhost:5555

# Run envsubst for config.js only and start nginx
CMD ["/bin/sh", "-c", "envsubst '${API_URL}' < /etc/config.template.js > /usr/share/nginx/html/js/config.js && exec nginx -g 'daemon off;'"]

EXPOSE 80

