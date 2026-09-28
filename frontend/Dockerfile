FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Used by `make test`: runs the Jest suite in the same image every time.
FROM deps AS test
COPY . .
CMD ["npm", "test"]

FROM deps AS build
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS web
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
