# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Build the site
hugo

# Dev server with live reload
hugo server

# Build for production (matches CI)
hugo --gc --minify

# Update Hugo module dependencies
hugo mod tidy

# Check module graph
hugo mod graph
```

Requires: Hugo extended (v0.155.3+), Go, Dart Sass. All installed via Homebrew.

## Architecture

This is a Hugo photo gallery site deployed to GitHub Pages via GitHub Actions.

**Theme:** `github.com/bep/galleriesdeluxe` imported as a Hugo Module (not git submodule — `themes/` dir is empty). The theme depends on `github.com/bep/gallerydeluxe` for individual gallery rendering and `github.com/bep/hugo-mod-misc/common-partials` for SEO.

**Deployment:** Push to `main` triggers `.github/workflows/hugo.yml` which installs Hugo + Dart Sass + Go, builds the site, and deploys to GitHub Pages at `https://coldsteam-studio.github.io/eyes-of-wadzi/`.

## Theme Overrides

The site overrides two theme partials and the JS/SCSS assets:

- `layouts/partials/gallerydeluxe/init.html` — adds `"title"` field to image JSON data for caption support (overrides gallerydeluxe module)
- `layouts/partials/galleriesdeluxe/header.html` — simplified nav showing only gallery list on every page (overrides galleriesdeluxe module)
- `assets/js/gallerydeluxe/src/index.js` — adds lightbox caption display when image title differs from filename
- `assets/js/gallerydeluxe/src/helpers.js` and `pig.js` — copied from theme (required since index.js is overridden)
- `assets/scss/galleriesdeluxe/vars-custom.scss` — caption styling for lightbox overlay

## Content Structure

Galleries are Hugo page bundles under `content/galleries/`:

```
content/galleries/my-gallery/
├── index.md          # front matter: title, date, categories, resources
├── photo1.jpg
└── photo2.jpg
```

Image captions are set via `resources` in front matter:

```yaml
resources:
  - src: photo1.jpg
    title: "Caption text here"
```

The `content/galleries/_index.md` file is required by the theme for the galleries list page.

## Key Config

`hugo.toml` uses `dartsass` transpiler (not libsass — libsass breaks with `hugo:vars` import). Gallery settings are under `[params.gallerydeluxe]`.
