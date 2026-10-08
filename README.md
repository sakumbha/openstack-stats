# OpenStack Contribution Card

A small SVG card for a GitHub profile README, generated from Stackalytics.

## Add to your profile README

After pushing this repository to GitHub, add:

```html
<p align="center">
  <a href="https://www.stackalytics.io/?user_id=sakumbha&metric=person-day">
    <img src="https://raw.githubusercontent.com/sakumbha/openstack-stats/main/card.svg" alt="OpenStack contribution statistics for sakumbha" width="980">
  </a>
</p>
```

Replace `openstack-stats` if you choose a different repository name.

## How it works

- `generate_card.py` calls the Stackalytics JSON API.
- It calculates total person-day effort and the Glance/Manila portions.
- `.github/workflows/update-card.yml` regenerates the SVG weekly and commits it.
- `workflow_dispatch` lets you refresh it manually.

Stackalytics documents the `/api/1.0/stats/modules` endpoint and supports `release`, `project_type`, `module`, `company`, `user_id`, and `metric` filters.
