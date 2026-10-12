# Snapframe actor: website screenshots & PDFs
FROM apify/actor-python-playwright:3.12

# Fonts for faithful rendering, including Arabic/RTL (Noto Naskh/Kufi-style coverage)
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto fonts-noto-core \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

COPY requirements.txt ./
# Install the Apify SDK explicitly (not guaranteed present in every base image
# tag). This can resolve a newer Playwright via apify -> crawlee, so reinstall
# the matching Chromium browsers right after to keep driver and browsers in sync.
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . ./

CMD ["python3", "-m", "src"]
