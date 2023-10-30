# Restore the original hosts file
sudo cp /etc/hosts.bak /etc/hosts

# # Make a copy
# sudo cp /etc/hosts /etc/hosts.bak

echo "$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'  ivy-picotls-standalone) ivy-standalone" | sudo tee -a /etc/hosts
echo "$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'  ivy-visualizer) ivy-visualizer" | sudo tee -a /etc/hosts