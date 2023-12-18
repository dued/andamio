#!/bin/bash
# INSTALADOR DE DUED COMO SERVICIO EN PRODUCCION CON AWS-LIGHTSAIL
sudo dnf update

# instale prerequisitos
sudo dnf install docker git -y

# el usuario que instala por defecto debe estar en el grupo docker
sudo groupadd docker
sudo usermod -aG docker ${USER}

# El servicio docker es un requisito para el demonio dued.
sudo service docker start

# instala docker-compose (latest version) y agrega permisos
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose


PATH_DUED_DAEMON="/srv/dued"
sudo mkdir -p ${PATH_DUED_DAEMON}
sudo git clone https://github.com/dued/andamio.git ${PATH_DUED_DAEMON}
sudo chown -R ${USER}:${USER} ${PATH_DUED_DAEMON}
sudo chmod 640 ${PATH_DUED_DAEMON}/.env


# Creamos el servicio a partir del docker-compose.yml en /srv/dued
# si cambia este directorio, cambie el archivo de sistema dued.service en
# WorkingDirectory=[lo que tengas abajo]
sudo curl -o /etc/systemd/system/dued.service https://raw.githubusercontent.com/dued/andamio/main/resources/dued.service
sudo chmod +x /etc/systemd/system/dued.service
sudo systemctl enable dued

echo -e "*** Creado el archivo de variables de entorno  ***"
echo -e "*** debes editarlo y usarlo solo en producción ***"
echo -e "inicie la aplicación a través de docker-compose:\n\n"
echo -e "docker-compose -f ${PATH_DUED_DAEMON}/docker-compose.yml up -d"
