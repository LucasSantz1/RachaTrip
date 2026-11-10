FROM node:24-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci && chown -R node:node /app
COPY --chown=node:node . .
RUN mkdir -p /app/.next && chown node:node /app/.next
USER node
EXPOSE 3000
CMD npm run dev -- -H 0.0.0.0
