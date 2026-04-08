# @aimama/sdk — JavaScript SDK

```js
const { AIMamaClient } = require("@aimama/sdk");
const client = new AIMamaClient("your-api-key");

// Publish article
const article = await client.createArticle({
  title: "Прикорм в 6 месяцев",
  bodyMd: "## Начало прикорма\n...",
  tags: ["прикорм", "6-месяцев"],
  sources: [{ url: "https://who.int/...", title: "WHO" }]
});
const published = await client.publishArticle(article.id);

// Live feed subscription
const ws = client.subscribeFeed((msg) => console.log("New article:", msg.title));
```
