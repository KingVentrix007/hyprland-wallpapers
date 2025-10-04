mpvpaper -o "--loop --hwdec=auto" DP-1 ~/Documents/Wallpapers/big-city-split-fiction-moewalls-com.mp4 &
sleep 3
swww img ~/Documents/Wallpapers/wp7370112-cyber-city-wallpapers.jpg --transition-type grow --transition-duration 0.3 --outputs DP-1
sleep 0.3
pkill mpvpaper
swww img ~/Documents/Wallpapers/wp7370112-cyber-city-wallpapers.jpg --transition-type fade --transition-duration 0.6 --outputs DP-1