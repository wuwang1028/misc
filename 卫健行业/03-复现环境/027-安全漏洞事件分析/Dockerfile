FROM php:7.4-apache

RUN a2enmod rewrite

WORKDIR /var/www/html

COPY app/ /var/www/html/
COPY docker/php.ini /usr/local/etc/php/conf.d/zzz-027.ini
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /var/www/html/uploads \
    && chown -R www-data:www-data /var/www/html/uploads

ENV SECRET_KEY="Go to the flag!"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["apache2-foreground"]
