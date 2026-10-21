FROM wazuh/wazuh-manager:4.14.1@sha256:a6df0df2831ad80d3d390626b1fd1d14fc91429b7196fe9df189d96899209e33
# El laboratorio conserva analysisd y logcollector, sin envio a un indexador.
RUN rm -rf /etc/services.d/filebeat && rm -f /etc/cont-init.d/1-config-filebeat
