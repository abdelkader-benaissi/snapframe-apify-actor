# Snapframe actor: website screenshots & PDFs
FROM apify/actor-python-playwright:3.12

# Fonts for faithful rendering, including Arabic/RTL (Noto Naskh/Kufi-style coverage)
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto fonts-noto-core \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

# The base image already ships the Apify SDK and Playwright with matching
# browser binaries; only project extras go here (deliberately no playwright pin,
# to avoid a version mismatch with the image's bundled Chromium).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["python3", "-m", "src"]
