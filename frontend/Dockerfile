# Build the static Svelte app...
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ...then serve it from Caddy. /api/* is reverse-proxied to the backend
# compose service (see Caddyfile) so the browser only ever talks to this
# one origin -- same reasoning as the Vite dev proxy, just for prod.
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80
