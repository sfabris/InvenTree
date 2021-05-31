
<img src="images/logo/inventree.png" alt="InvenTree" width="128"/>

# InvenTree

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage Status](https://coveralls.io/repos/github/inventree/InvenTree/badge.svg)](https://coveralls.io/github/inventree/InvenTree)
![PEP](https://github.com/inventree/inventree/actions/workflows/style.yaml/badge.svg)
![SQLite](https://github.com/inventree/inventree/actions/workflows/coverage.yaml/badge.svg)
![MySQL](https://github.com/inventree/inventree/actions/workflows/mysql.yaml/badge.svg)
![PostgreSQL](https://github.com/inventree/inventree/actions/workflows/postgresql.yaml/badge.svg)


InvenTree is an open-source Inventory Management System which provides powerful low-level stock control and part tracking. The core of the InvenTree system is a Python/Django database backend which provides an admin interface (web-based) and a JSON API for interaction with external interfaces and applications.

InvenTree is designed to be lightweight and easy to use for SME or hobbyist applications, where many existing stock management solutions are bloated and cumbersome to use. Updating stock is a single-action process and does not require a complex system of work orders or stock transactions. 

However, powerful business logic works in the background to ensure that stock tracking history is maintained, and users have ready access to stock level information.

# Docker

[![Docker Pulls](https://img.shields.io/docker/pulls/inventree/inventree)](https://hub.docker.com/r/inventree/inventree)
![Docker Build](https://github.com/inventree/inventree/actions/workflows/docker_build.yaml/badge.svg)

InvenTree is [available via Docker](https://hub.docker.com/r/inventree/inventree). Read the [docker guide](https://inventree.readthedocs.io/en/latest/start/docker/) for full details.

# Companion App

InvenTree is supported by a [companion mobile app](https://inventree.readthedocs.io/en/latest/app/app/) which allows users access to stock control information and functionality. 

[**Download InvenTree from the Android Play Store**](https://play.google.com/store/apps/details?id=inventree.inventree_app)

*Currently the mobile app is only availble for Android*

# Translation

![de translation](https://img.shields.io/badge/dynamic/json?color=blue&label=de&style=flat&query=%24.progress.0.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![es-ES translation](https://img.shields.io/badge/dynamic/json?color=blue&label=es-ES&style=flat&query=%24.progress.1.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![fr translation](https://img.shields.io/badge/dynamic/json?color=blue&label=fr&style=flat&query=%24.progress.3.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![it translation](https://img.shields.io/badge/dynamic/json?color=blue&label=it&style=flat&query=%24.progress.4.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![pl translation](https://img.shields.io/badge/dynamic/json?color=blue&label=pl&style=flat&query=%24.progress.5.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![ru translation](https://img.shields.io/badge/dynamic/json?color=blue&label=ru&style=flat&query=%24.progress.6.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![tr translation](https://img.shields.io/badge/dynamic/json?color=blue&label=tr&style=flat&query=%24.progress.6.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)
![zh-CN translation](https://img.shields.io/badge/dynamic/json?color=blue&label=zh-CN&style=flat&query=%24.progress.7.data.translationProgress&url=https%3A%2F%2Fbadges.awesome-crowdin.com%2Fstats-14720186-452300.json)

Native language translation of the InvenTree web application is [community contributed via crowdin](https://crowdin.com/project/inventree). **Contributions are welcomed and encouraged**.

To contribute to the translation effort, navigate to the [InvenTree crowdin project](https://crowdin.com/project/inventree), create a free account, and start making translations suggestions for your language of choice!

# Documentation

For InvenTree documentation, refer to the [InvenTree documentation website](https://inventree.readthedocs.io/en/latest/).

# Getting Started

Refer to the [getting started guide](https://inventree.readthedocs.io/en/latest/start/install/) for installation and setup instructions.

# Credits

The credits for all used packages are part of the [InvenTree documentation website](https://inventree.readthedocs.io/en/latest/credits/).

# Integration

InvenTree is designed to be extensible, and provides multiple options for integration with external applications or addition of custom plugins:

* [InvenTree API](https://inventree.readthedocs.io/en/latest/extend/api/)
* [Python module](https://inventree.readthedocs.io/en/latest/extend/python)
* [Plugin interface](https://inventree.readthedocs.io/en/latest/extend/plugins)
* [Third party](https://inventree.readthedocs.io/en/latest/extend/integrate)

# Contributing

Contributions are welcomed and encouraged. Please help to make this project even better! Refer to the [contribution page](https://inventree.readthedocs.io/en/latest/contribute/).

# Donate

If you use InvenTree and find it to be useful, please consider making a donation toward its continued development. 

[Donate via PayPal](https://paypal.me/inventree?locale.x=en_AU)
