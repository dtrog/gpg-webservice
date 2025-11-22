FROM nginx:alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static files
COPY index.html /usr/share/nginx/html/
COPY register.html /usr/share/nginx/html/
COPY login.html /usr/share/nginx/html/
COPY profile.html /usr/share/nginx/html/
COPY debug.html /usr/share/nginx/html/
COPY admin.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
