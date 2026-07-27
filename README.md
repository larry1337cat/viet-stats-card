# Viet Stats Card

A GitHub stats card, rendered as a live SVG, with labels in Vietnamese and a custom theme. Built for embedding in `README.md` profile pages - same idea as `github-readme-stats`, but self-hosted, dependency-free, and localized.

## Demo

**Dark, bar chart**

![Dark bar](https://viet-stats-card.vercel.app/api/stats?username=larry1337-cat&theme=dark&chart=bar)

**Dark, pie chart**

![Dark pie](https://viet-stats-card.vercel.app/api/stats?username=larry1337-cat&theme=dark&chart=pie)

**Light, bar chart**

![Light bar](https://viet-stats-card.vercel.app/api/stats?username=larry1337-cat&theme=light&chart=bar)

**Light, pie chart**

![Light pie](https://viet-stats-card.vercel.app/api/stats?username=larry1337-cat&theme=light&chart=pie)

## Usage

```markdown
![Viet Stats Card](https://viet-stats-card.vercel.app/api/stats?username=YOUR_GITHUB_USERNAME&theme=dark&chart=bar&langs_count=5)
```

Query parameters:

| Param           | Values          | Default | Description                                  |
|-----------------|-----------------|---------|-----------------------------------------------|
| `username`      | any GitHub user | —       | required                                       |
| `theme`         | `dark`, `light` | `dark`  | color theme of the card                        |
| `chart`         | `bar`, `pie`    | `bar`   | language breakdown chart style                 |
| `include_forks` | `true`, `false` | `false` | include forked repos in language stats         |
| `langs_count`   | `5`-`10`        | `5`     | number of languages shown in the breakdown     |

## What it shows

- Public repositories
- Total stars received across all repos
- Followers
- Following
- Language breakdown by code size (bar or pie), forks excluded by default, top 5 to 10 languages via `langs_count`

## Deploy your own

1. Fork this repo
2. Go to [vercel.com](https://vercel.com), sign in with GitHub
3. **Add New Project** → import your fork → **Deploy**
4. (Optional but recommended) In **Project Settings → Environment Variables**, add:
   - `GH_TOKEN` = a GitHub Personal Access Token (no special scopes needed for public data)
   - Raises the GitHub API rate limit from 60/hour to 5,000/hour — needed since language stats fetch each repo individually
5. Your card is live at `https://<your-project>.vercel.app/api/stats?username=<you>`

## Local development

```bash
npm i -g vercel
vercel dev
```

Then open `http://localhost:3000/api/stats?username=YOUR_USERNAME`.

## Why this exists

Popular public stat-card services get rate-limited and slow because they're shared by millions of profiles. This is a small, self-hosted alternative — no dependencies, easy to fork, easy to read, and easy to extend with your own stats or your own language.

## Contributing

Issues and pull requests are welcome — new stat rows, new themes, and fixes to the GitHub API handling are all fair game.

## License

MIT
