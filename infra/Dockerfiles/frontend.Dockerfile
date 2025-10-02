FROM node:20-alpine AS base
WORKDIR /app

COPY apps/frontend/package.json apps/frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps || true

COPY apps/frontend ./

EXPOSE 3000
CMD ["npm", "run", "dev"]
