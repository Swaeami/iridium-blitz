#!/bin/bash

source /etc/hysteria/core/scripts/utils.sh
source /etc/hysteria/core/scripts/path.sh
source /etc/hysteria/core/scripts/services_status.sh >/dev/null 2>&1

check_services() {
    for service in "${services[@]}"; do
        service_base_name=$(basename "$service" .service)
        display_name=$(echo "$service_base_name" | sed -E 's/hysteria-//; s/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')

        if systemctl is-active --quiet "$service"; then
            echo -e "  ${green}●${NC} ${display_name}"
        else
            echo -e "  ${gray}○${NC} ${DIM}${display_name}${NC}"
        fi
    done
}

hysteria2_install_handler() {
    if systemctl is-active --quiet hysteria-server.service; then
        echo "The hysteria-server.service is currently active."
        echo "If you need to update the core, please use the 'Update Core' option."
        return
    fi

    while true; do
        read -p "Enter the SNI (default: bts.com): " sni
        sni=${sni:-bts.com}

        read -p "Enter the port number you want to use: " port
        if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
            echo "Invalid port number. Please enter a number between 1 and 65535."
        else
            break
        fi
    done


    python3 $CLI_PATH install-hysteria2 --port "$port" --sni "$sni"

    cat <<EOF > /etc/hysteria/.configs.env
SNI=$sni
EOF
    python3 $CLI_PATH ip-address
}

hysteria2_add_user_handler() {
    while true; do
        read -p "Enter the username: " username

        if [[ "$username" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            if [[ -n $(python3 $CLI_PATH get-user -u "$username" 2>/dev/null) ]]; then
                echo -e "${red}Error:${NC} Username already exists. Please choose another username."
            else
                break
            fi
        else
            echo -e "${red}Error:${NC} Username can only contain letters and numbers."
        fi
    done

    read -p "Enter the traffic limit (in GB): " traffic_limit_GB
    read -p "Enter the expiration days: " expiration_days

    local unlimited_arg=""
    while true; do
        read -p "Exempt user from IP limit checks (unlimited IP)? (y/n) [n]: " unlimited_choice
        case "$unlimited_choice" in
            y|Y) unlimited_arg="--unlimited"; break ;;
            n|N|"") break ;;
            *) echo -e "${red}Error:${NC} Please answer 'y' or 'n'." ;;
        esac
    done

    creation_date=$(date +%Y-%m-%d)

    python3 $CLI_PATH add-user --username "$username" --traffic-limit "$traffic_limit_GB" --expiration-days "$expiration_days" --creation-date "$creation_date" $unlimited_arg
}

hysteria2_edit_user_handler() {
    prompt_for_input() {
        local prompt_message="$1"
        local validation_regex="$2"
        local default_value="$3"
        local input_variable_name="$4"

        while true; do
            read -p "$prompt_message" input
            if [[ -z "$input" ]]; then
                input="$default_value"
            fi
            if [[ "$input" =~ $validation_regex ]]; then
                eval "$input_variable_name='$input'"
                break
            else
                echo -e "${red}Error:${NC} Invalid input. Please try again."
            fi
        done
    }

    prompt_for_input "Enter the username you want to edit: " '^[a-zA-Z0-9_-]+$' '' username

    user_exists_output=$(python3 $CLI_PATH get-user -u "$username" 2>&1)
    if [[ -z "$user_exists_output" ]]; then
        echo -e "${red}Error:${NC} User '$username' not found or an error occurred."
        return 1
    fi

    prompt_for_input "Enter the new username (leave empty to keep the current username): " '^[a-zA-Z0-9_-]*$' '' new_username

    prompt_for_input "Enter the new traffic limit (in GB) (leave empty to keep the current limit): " '^[0-9]*$' '' new_traffic_limit_GB

    prompt_for_input "Enter the new expiration days (leave empty to keep the current expiration days): " '^[0-9]*$' '' new_expiration_days

    while true; do
        read -p "Do you want to generate a new password? (y/n) [n]: " renew_password
        case "$renew_password" in
            y|Y) renew_password=true; break ;;
            n|N|"") renew_password=false; break ;;
            *) echo -e "${red}Error:${NC} Please answer 'y' or 'n'." ;;
        esac
    done

    while true; do
        read -p "Do you want to generate a new creation date? (y/n) [n]: " renew_creation_date
        case "$renew_creation_date" in
            y|Y) renew_creation_date=true; break ;;
            n|N|"") renew_creation_date=false; break ;;
            *) echo -e "${red}Error:${NC} Please answer 'y' or 'n'." ;;
        esac
    done

    local blocked_arg=""
    while true; do
        read -p "Change user block status? ([b]lock/[u]nblock/[s]kip) [s]: " block_user
        case "$block_user" in
            b|B) blocked_arg="--blocked"; break ;;
            u|U) blocked_arg="--unblocked"; break ;;
            s|S|"") break ;;
            *) echo -e "${red}Error:${NC} Please answer 'b', 'u', or 's'." ;;
        esac
    done

    local ip_limit_arg=""
    while true; do
        read -p "Change IP limit status? ([u]nlimited/[l]imited/[s]kip) [s]: " ip_limit_status
        case "$ip_limit_status" in
            u|U) ip_limit_arg="--unlimited-ip"; break ;;
            l|L) ip_limit_arg="--limited-ip"; break ;;
            s|S|"") break ;;
            *) echo -e "${red}Error:${NC} Please answer 'u', 'l', or 's'." ;;
        esac
    done

    args=()
    if [[ -n "$new_username" ]]; then args+=("--new-username" "$new_username"); fi
    if [[ -n "$new_traffic_limit_GB" ]]; then args+=("--new-traffic-limit" "$new_traffic_limit_GB"); fi
    if [[ -n "$new_expiration_days" ]]; then args+=("--new-expiration-days" "$new_expiration_days"); fi
    if [[ "$renew_password" == "true" ]]; then args+=("--renew-password"); fi
    if [[ "$renew_creation_date" == "true" ]]; then args+=("--renew-creation-date"); fi
    if [[ -n "$blocked_arg" ]]; then args+=("$blocked_arg"); fi
    if [[ -n "$ip_limit_arg" ]]; then args+=("$ip_limit_arg"); fi

    python3 $CLI_PATH edit-user --username "$username" "${args[@]}"
}

hysteria2_remove_user_handler() {
    while true; do
        read -p "Enter the username: " username

        if [[ "$username" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            break
        else
            echo -e "${red}Error:${NC} Username can only contain letters and numbers."
        fi
    done
    python3 $CLI_PATH remove-user "$username"
}

hysteria2_get_user_handler() {
    while true; do
        read -p "Enter the username: " username
        if [[ "$username" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            break
        else
            echo -e "${red}Error:${NC} Username can only contain letters and numbers."
        fi
    done

    user_data=$(python3 "$CLI_PATH" get-user --username "$username" 2>/dev/null)
    local exit_code=$?

    if [[ $exit_code -ne 0 || -z "$user_data" ]]; then
        echo -e "${red}Error:${NC} User '$username' not found or invalid response."
        return 1
    fi

    if ! echo "$user_data" | jq -e . > /dev/null 2>&1; then
        echo -e "${red}Error:${NC} Received invalid data for user '$username'."
        return 1
    fi

    password=$(echo "$user_data" | jq -r '.password // "N/A"')
    max_download_bytes=$(echo "$user_data" | jq -r '.max_download_bytes // 0')
    upload_bytes=$(echo "$user_data" | jq -r '.upload_bytes // 0')
    download_bytes=$(echo "$user_data" | jq -r '.download_bytes // 0')
    account_creation_date=$(echo "$user_data" | jq -r '.account_creation_date // "N/A"')
    expiration_days=$(echo "$user_data" | jq -r '.expiration_days // 0')
    blocked=$(echo "$user_data" | jq -r '.blocked // false')
    status=$(echo "$user_data" | jq -r '.status // "N/A"')
    total_usage=$((upload_bytes + download_bytes))
    max_download_gb=$(echo "scale=2; $max_download_bytes / 1073741824" | bc)
    upload_gb=$(echo "scale=2; $upload_bytes / 1073741824" | bc)
    download_gb=$(echo "scale=2; $download_bytes / 1073741824" | bc)
    total_usage_gb=$(echo "scale=2; $total_usage / 1073741824" | bc)

    local expiration_date_str="N/A"
    local used_days_str="N/A"

    if [[ "$account_creation_date" != "N/A" ]]; then
        expiration_date_str=$(date -d "$account_creation_date + $expiration_days days" +"%Y-%m-%d")
        current_date=$(date +"%Y-%m-%d")
        used_days=$(( ( $(date -d "$current_date" +%s) - $(date -d "$account_creation_date" +%s) ) / 86400 ))

        if [[ $used_days -lt 0 ]]; then
            used_days=0
        fi

        if [[ $used_days -gt $expiration_days ]]; then
            used_days=$expiration_days
        fi
        used_days_str=$used_days
    fi

    echo -e "${green}User Details:${NC}"
    echo -e "Username:         $username"
    echo -e "Password:         $password"
    echo -e "Total Traffic:    $max_download_gb GB"
    echo -e "Total Usage:      $total_usage_gb GB"
    echo -e "Time Expiration:  $expiration_date_str ($used_days_str/$expiration_days Days)"
    echo -e "Blocked:          $blocked"
    echo -e "Status:           $status"
}

hysteria2_list_users_handler() {
    users_json=$(python3 $CLI_PATH list-users 2>/dev/null)
    local exit_code=$?

    if [ $exit_code -ne 0 ] || [ -z "$users_json" ]; then
        echo -e "${red}Error:${NC} Failed to list users."
        return 1
    fi
    
    if ! echo "$users_json" | jq -e . > /dev/null 2>&1; then
        echo -e "${red}Error:${NC} Received invalid data while listing users."
        return 1
    fi

    user_count=$(echo "$users_json" | jq 'length')

    if [ "$user_count" -eq 0 ]; then
        echo -e "${yellow}No users found.${NC}"
        return 1
    fi

    printf "%-20s %-20s %-15s %-20s %-30s %-10s %-15s %-15s %-15s\n" \
        "Username" "Traffic(GB)" "Expiry(Days)" "Created" "Password" "Blocked" "Status" "Down(MB)" "Up(MB)"

    echo "$users_json" | jq -r '.[] |
        [.username,
         (if .max_download_bytes == 0 then "Unlimited" else (.max_download_bytes / 1073741824 | tostring) end),
         (if .expiration_days == 0 then "Never" else (.expiration_days | tostring) end),
         (.account_creation_date // "N/A"),
         .password,
         .blocked,
         .status,
         ((.download_bytes // 0) / 1048576 | floor),
         ((.upload_bytes // 0) / 1048576 | floor)] |
        @tsv' | \
    while IFS=$'\t' read -r username traffic expiry created password blocked status down up; do
        printf "%-20s %-20s %-15s %-20s %-30s %-10s %-15s %-15s %-15s\n" \
            "$username" "$traffic" "$expiry" "$created" "$password" "$blocked" "$status" "$down" "$up"
    done
}

hysteria2_reset_user_handler() {
    while true; do
        read -p "Enter the username: " username

        if [[ "$username" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            break
        else
            echo -e "${red}Error:${NC} Username can only contain letters and numbers."
        fi
    done
    python3 $CLI_PATH reset-user --username "$username"
}

hysteria2_show_user_uri_handler() {
    check_service_active() {
        systemctl is-active --quiet "$1"
    }

    while true; do
        read -p "Enter the username: " username
        if [[ "$username" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            break
        else
            echo -e "${red}Error:${NC} Username can only contain letters and numbers."
        fi
    done

    flags=""

    if check_service_active "hysteria-singbox.service"; then
        flags+=" -s"
    fi

    if check_service_active "hysteria-normal-sub.service"; then
        flags+=" -n"
    fi

    if [[ -n "$flags" ]]; then
        python3 $CLI_PATH show-user-uri -u "$username" -a -qr $flags
    else
        python3 $CLI_PATH show-user-uri -u "$username" -a -qr
    fi
}


hysteria2_change_port_handler() {
    while true; do
        read -p "Enter the new port number you want to use: " port
        if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
            echo "Invalid port number. Please enter a number between 1 and 65535."
        else
            break
        fi
    done
    python3 $CLI_PATH change-hysteria2-port --port "$port"
}

hysteria2_change_sni_handler() {
    while true; do
        read -p "Enter the new SNI (e.g., example.com): " sni

        if [[ "$sni" =~ ^[a-zA-Z0-9.]+$ ]]; then
            break
        else
            echo -e "${red}Error:${NC} SNI can only contain letters, numbers, and dots."
        fi
    done

    python3 $CLI_PATH change-hysteria2-sni --sni "$sni"

    if systemctl is-active --quiet hysteria-singbox.service; then
        systemctl restart hysteria-singbox.service
    fi
}

edit_ips() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🌍 IP/Domain Manager${NC}\n"
        print_line
        menu_item "1" "Change IPv4 / Domain" "$cyan"
        menu_item "2" "Change IPv6 / Domain" "$cyan"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s choice
        echo

        case $choice in
            1)
                echo
                prompt_default "New IPv4 or Domain" "" new_ip4
                if [[ -n "$new_ip4" ]]; then
                    python3 "$CLI_PATH" ip-address --edit -4 "$new_ip4"
                    print_success "IPv4 updated to $new_ip4"
                fi
                wait_seconds 2
                ;;
            2)
                echo
                prompt_default "New IPv6 or Domain" "" new_ip6
                if [[ -n "$new_ip6" ]]; then
                    python3 "$CLI_PATH" ip-address --edit -6 "$new_ip6"
                    print_success "IPv6 updated to $new_ip6"
                fi
                wait_seconds 2
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

hysteria_upgrade(){
    bash <(curl https://raw.githubusercontent.com/Swaeami/iridium-blitz/main/upgrade.sh)
}

warp_configure_handler() {
    local service_name="wg-quick@wgcf.service"

    if ! systemctl is-active --quiet "$service_name"; then
        print_error "WARP service not running. Start it first."
        wait_seconds 2
        return
    fi

    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🌐 WARP Configuration${NC}\n"
        
        # Get current status
        status_json=$(python3 $CLI_PATH warp-status 2>/dev/null)
        all_traffic=$(echo "$status_json" | grep -o '"all_traffic_via_warp": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        popular_sites=$(echo "$status_json" | grep -o '"popular_sites_via_warp": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        domestic_sites=$(echo "$status_json" | grep -o '"domestic_sites_via_warp": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        block_adult=$(echo "$status_json" | grep -o '"block_adult_content": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        
        # Display status
        local st_all=$([[ "$all_traffic" == "true" ]] && echo "${green}ON${NC}" || echo "${gray}OFF${NC}")
        local st_pop=$([[ "$popular_sites" == "true" ]] && echo "${green}ON${NC}" || echo "${gray}OFF${NC}")
        local st_dom=$([[ "$domestic_sites" == "true" ]] && echo "${green}ON${NC}" || echo "${gray}OFF${NC}")
        local st_adult=$([[ "$block_adult" == "true" ]] && echo "${green}ON${NC}" || echo "${gray}OFF${NC}")
        
        echo -e "  All Traffic: $st_all  │  Popular Sites: $st_pop"
        echo -e "  Domestic: $st_dom  │  Block Adult: $st_adult"
        echo
        print_line
        print_section "Toggle Options"
        menu_item "1" "All traffic via WARP" "$cyan"
        menu_item "2" "Popular sites via WARP" "$cyan"
        menu_item "3" "Domestic sites via WARP" "$cyan"
        menu_item "4" "Block adult content" "$cyan"
        print_section "Management"
        menu_item "5" "Show WARP Status" "$yellow"
        menu_item "6" "Change WARP IP" "$yellow"
        menu_item "7" "Switch to WARP Plus" "$green"
        menu_item "8" "Switch to Normal WARP" "$gray"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                target_state=$([[ "$all_traffic" == "true" ]] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-all "$target_state"
                wait_seconds 1
                ;;
            2)
                target_state=$([[ "$popular_sites" == "true" ]] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-popular-sites "$target_state"
                wait_seconds 1
                ;;
            3)
                target_state=$([[ "$domestic_sites" == "true" ]] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-domestic-sites "$target_state"
                wait_seconds 1
                ;;
            4)
                target_state=$([[ "$block_adult" == "true" ]] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-block-adult-sites "$target_state"
                wait_seconds 1
                ;;
            5)
                echo
                current_ip=$(curl -s --interface wgcf --connect-timeout 2 http://v4.ident.me || echo "N/A")
                cd /etc/warp/ && wgcf status 2>/dev/null
                echo -e "\n  ${cyan}WARP IP:${NC} ${green}${current_ip}${NC}"
                wait_seconds 5
                ;;
            6)
                print_info "Changing WARP IP..."
                old_ip=$(curl -s --interface wgcf --connect-timeout 2 http://v4.ident.me || echo "N/A")
                systemctl restart "$service_name"
                sleep 3
                new_ip=$(curl -s --interface wgcf --connect-timeout 2 http://v4.ident.me || echo "N/A")
                echo -e "  ${gray}Old:${NC} $old_ip → ${green}New:${NC} $new_ip"
                wait_seconds 3
                ;;
            7)
                echo
                prompt_default "WARP Plus license key" "" warp_key
                if [[ -n "$warp_key" ]]; then
                    systemctl stop "$service_name" 2>/dev/null
                    cd /etc/warp/ && WGCF_LICENSE_KEY="$warp_key" wgcf update
                    systemctl start "$service_name"
                    python3 "$CLI_PATH" restart-hysteria2 > /dev/null 2>&1
                    print_success "Switched to WARP Plus"
                else
                    print_error "Key required"
                fi
                wait_seconds 2
                ;;
            8)
                if confirm "Create new WARP account?" "n"; then
                    systemctl stop "$service_name" 2>/dev/null
                    cd /etc/warp/ && rm -f wgcf-account.toml && yes | wgcf register
                    systemctl start "$service_name"
                    python3 "$CLI_PATH" restart-hysteria2 > /dev/null 2>&1
                    print_success "Switched to Normal WARP"
                    wait_seconds 2
                fi
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

telegram_bot_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  📱 Telegram Bot${NC}\n"
        print_line
        menu_item "1" "Start Telegram bot" "$green"
        menu_item "2" "Stop Telegram bot" "$red"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                if systemctl is-active --quiet hysteria-telegram-bot.service; then
                    print_warning "Telegram bot is already running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "Telegram bot token" "" token
                    [[ -z "$token" ]] && { print_error "Token required"; wait_seconds 2; continue; }
                    
                    prompt_default "Admin IDs (comma-separated)" "" admin_ids
                    [[ -z "$admin_ids" ]] && { print_error "Admin IDs required"; wait_seconds 2; continue; }
                    
                    python3 $CLI_PATH telegram -a start -t "$token" -aid "$admin_ids"
                    wait_seconds 2
                fi
                ;;
            2)
                if confirm "Stop Telegram bot?" "n"; then
                    python3 $CLI_PATH telegram -a stop
                    wait_seconds 2
                fi
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

singbox_handler() {
    echo -e "${red} Deprecated${NC}"
}

normalsub_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🔗 Normal-SUB Service${NC}\n"
        print_line
        menu_item "1" "Start service" "$green"
        menu_item "2" "Stop service" "$red"
        menu_item "3" "Change SUBPATH" "$yellow"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                if systemctl is-active --quiet hysteria-normal-sub.service; then
                    print_warning "Normal-Sub is already running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "Domain for SSL" "" domain
                    [[ -z "$domain" ]] && { print_error "Domain required"; wait_seconds 2; continue; }
                    
                    prompt_default "Port number" "443" port
                    python3 $CLI_PATH normal-sub -a start -d "$domain" -p "$port"
                    wait_seconds 2
                fi
                ;;
            2)
                if ! systemctl is-active --quiet hysteria-normal-sub.service; then
                    print_warning "Normal-Sub is already stopped"
                    wait_seconds 2
                else
                    if confirm "Stop Normal-Sub?" "n"; then
                        python3 $CLI_PATH normal-sub -a stop
                        wait_seconds 2
                    fi
                fi
                ;;
            3)
                if ! systemctl is-active --quiet hysteria-normal-sub.service; then
                    print_error "Start service first"
                    wait_seconds 2
                    continue
                fi
                echo
                prompt_default "New SUBPATH (A-Z, a-z, 0-9)" "" subpath
                if [[ -n "$subpath" ]] && [[ "$subpath" =~ [A-Z] ]] && [[ "$subpath" =~ [a-z] ]] && [[ "$subpath" =~ [0-9] ]]; then
                    python3 $CLI_PATH normal-sub -a edit_subpath -sp "$subpath"
                    wait_seconds 2
                else
                    print_error "Invalid SUBPATH format"
                    wait_seconds 2
                fi
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

webpanel_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🌐 Web Panel${NC}\n"
        
        # Show current status
        if systemctl is-active --quiet hysteria-webpanel.service; then
            echo -e "  ${green}●${NC} Service is ${green}running${NC}"
        else
            echo -e "  ${red}●${NC} Service is ${red}stopped${NC}"
        fi
        echo
        print_line
        menu_item "1" "Start WebPanel" "$green"
        menu_item "2" "Stop WebPanel" "$red"
        menu_item "3" "Show URL" "$cyan"
        menu_item "4" "Show API Token" "$cyan"
        menu_item "5" "Reset Credentials" "$yellow"
        menu_item "6" "Change Domain/Port" "$yellow"
        menu_item "7" "Change Root Path" "$yellow"
        menu_item "8" "Session Expiration" "$yellow"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                if systemctl is-active --quiet hysteria-webpanel.service; then
                    print_warning "WebPanel is already running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "Domain for SSL" "" domain
                    [[ -z "$domain" ]] && { print_error "Domain required"; wait_seconds 2; continue; }
                    
                    prompt_default "Port" "8443" port
                    prompt_default "Admin username" "admin" admin_username
                    
                    read -sp "$(echo -e "${IRIDIUM}?${NC} Admin password: ")" admin_password
                    echo
                    [[ -z "$admin_password" ]] && { print_error "Password required"; wait_seconds 2; continue; }
                    
                    python3 $CLI_PATH webpanel -a start -d "$domain" -p "$port" -au "$admin_username" -ap "$admin_password"
                    wait_seconds 2
                fi
                ;;
            2)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                    print_warning "WebPanel is already stopped"
                    wait_seconds 2
                else
                    if confirm "Stop WebPanel?" "n"; then
                        python3 $CLI_PATH webpanel -a stop
                        wait_seconds 2
                    fi
                fi
                ;;
            3)
                echo
                print_line
                url=$(python3 $CLI_PATH get-webpanel-url)
                echo -e "${cyan}$url${NC}"
                print_line
                wait_seconds 5
                ;;
            4)
                echo
                print_line
                api_token=$(python3 $CLI_PATH get-webpanel-api-token)
                echo -e "${cyan}$api_token${NC}"
                print_line
                wait_seconds 5
                ;;
            5)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                    print_error "Service not running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "New username (blank=keep)" "" new_username
                    read -sp "$(echo -e "${IRIDIUM}?${NC} New password (blank=keep): ")" new_password
                    echo
                    
                    local cmd_args=()
                    [[ -n "$new_username" ]] && cmd_args+=("-u" "$new_username")
                    [[ -n "$new_password" ]] && cmd_args+=("-p" "$new_password")
                    
                    if [[ ${#cmd_args[@]} -gt 0 ]]; then
                        python3 "$CLI_PATH" reset-webpanel-creds "${cmd_args[@]}"
                    else
                        print_warning "No changes"
                    fi
                    wait_seconds 2
                fi
                ;;
            6)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                    print_error "Service not running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "New domain (blank=keep)" "" new_domain
                    prompt_default "New port (blank=keep)" "" new_port
                    
                    local cmd_args=()
                    [[ -n "$new_domain" ]] && cmd_args+=("--domain" "$new_domain")
                    [[ -n "$new_port" ]] && cmd_args+=("--port" "$new_port")
                    
                    if [[ ${#cmd_args[@]} -gt 0 ]]; then
                        python3 "$CLI_PATH" change-webpanel-domain-port "${cmd_args[@]}"
                    else
                        print_warning "No changes"
                    fi
                    wait_seconds 2
                fi
                ;;
            7)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                    print_error "Service not running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "New root path (blank=random)" "" new_root_path
                    local cmd_args=()
                    [[ -n "$new_root_path" ]] && cmd_args+=("--path" "$new_root_path")
                    python3 "$CLI_PATH" change-webpanel-root "${cmd_args[@]}"
                    wait_seconds 2
                fi
                ;;
            8)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                    print_error "Service not running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "Session expiration (minutes)" "60" new_minutes
                    if [[ "$new_minutes" =~ ^[0-9]+$ ]]; then
                        python3 "$CLI_PATH" change-webpanel-exp --minutes "$new_minutes"
                    else
                        print_error "Invalid number"
                    fi
                    wait_seconds 2
                fi
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

obfs_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🔐 OBFS Management${NC}\n"
        print_line
        menu_item "1" "Remove OBFS" "$red"
        menu_item "2" "Generate new OBFS" "$green"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                if confirm "Remove OBFS?" "n"; then
                    python3 $CLI_PATH manage_obfs -r
                    wait_seconds 2
                fi
                ;;
            2)
                python3 $CLI_PATH manage_obfs -g
                wait_seconds 2
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

geo_update_handler() {
    clear
    echo -e "${IRIDIUM}${BOLD}  🌍 Geo Files${NC}\n"
    print_line
    menu_item "1" "Update Iran Geo" "$cyan"
    menu_item "2" "Update China Geo" "$cyan"
    menu_item "3" "Update Russia Geo" "$cyan"
    menu_item "4" "Check Current Files" "$yellow"
    menu_item "0" "← Back" "$gray"
    print_line
    echo -ne "\n${IRIDIUM}❯${NC} "
    read -n 1 -s option
    echo

    case $option in
        1)
            print_info "Updating Iran Geo Files..."
            python3 $CLI_PATH update-geo --country iran
            ;;
        2)
            print_info "Updating China Geo Files..."
            python3 $CLI_PATH update-geo --country china
            ;;
        3)
            print_info "Updating Russia Geo Files..."
            python3 $CLI_PATH update-geo --country russia
            ;;
        4)
            echo
            print_section "Geo Files Info"
            if [ -f "/etc/hysteria/geosite.dat" ]; then
                echo -e "  ${cyan}GeoSite:${NC} $(ls -lh /etc/hysteria/geosite.dat | awk '{print $5}')"
            else
                echo -e "  ${red}GeoSite:${NC} not found"
            fi
            if [ -f "/etc/hysteria/geoip.dat" ]; then
                echo -e "  ${cyan}GeoIP:${NC}   $(ls -lh /etc/hysteria/geoip.dat | awk '{print $5}')"
            else
                echo -e "  ${red}GeoIP:${NC}   not found"
            fi
            ;;
        0|q) ;;
        *) ;;
    esac
}

masquerade_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🎭 Masquerade${NC}\n"
        
        status=$(python3 $CLI_PATH masquerade -s)
        if [ "$status" == "Enabled" ]; then
            echo -e "  ${green}●${NC} Status: ${green}Enabled${NC}"
        else
            echo -e "  ${red}●${NC} Status: ${red}Disabled${NC}"
        fi
        echo
        print_line
        menu_item "1" "Enable Masquerade" "$green"
        menu_item "2" "Remove Masquerade" "$red"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                python3 $CLI_PATH masquerade -e
                wait_seconds 2
                ;;
            2)
                if confirm "Remove Masquerade?" "n"; then
                    python3 $CLI_PATH masquerade -r
                    wait_seconds 2
                fi
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

ip_limit_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🔒 IP Limiter${NC}\n"
        
        # Show current status
        if systemctl is-active --quiet hysteria-ip-limit.service; then
            echo -e "  ${green}●${NC} Service is ${green}running${NC}"
        else
            echo -e "  ${red}●${NC} Service is ${red}stopped${NC}"
        fi
        
        # Show current config
        local cur_block=$(grep '^BLOCK_DURATION=' /etc/hysteria/.configs.env 2>/dev/null | cut -d'=' -f2)
        local cur_max=$(grep '^MAX_IPS=' /etc/hysteria/.configs.env 2>/dev/null | cut -d'=' -f2)
        echo -e "  ${gray}Block:${NC} ${cur_block:-60}s  ${gray}│${NC}  ${gray}Max IPs:${NC} ${cur_max:-1}"
        echo
        print_line
        menu_item "1" "Start Service" "$green"
        menu_item "2" "Stop Service" "$red"
        menu_item "3" "Change Config" "$yellow"
        menu_item "0" "← Back" "$gray"
        print_line
        echo -ne "\n${IRIDIUM}❯${NC} "
        read -n 1 -s option
        echo

        case $option in
            1)
                if systemctl is-active --quiet hysteria-ip-limit.service; then
                    print_warning "IP Limiter is already running"
                    wait_seconds 2
                else
                    echo
                    prompt_default "Block Duration (seconds)" "60" block_duration
                    prompt_default "Default Max IPs per User" "1" max_ips
                    
                    python3 $CLI_PATH config-ip-limit --block-duration "$block_duration" --max-ips "$max_ips"
                    python3 $CLI_PATH start-ip-limit
                    wait_seconds 2
                fi
                ;;
            2)
                if ! systemctl is-active --quiet hysteria-ip-limit.service; then
                    print_warning "IP Limiter is already stopped"
                    wait_seconds 2
                else
                    if confirm "Stop IP Limiter?" "n"; then
                        python3 $CLI_PATH stop-ip-limit
                        wait_seconds 2
                    fi
                fi
                ;;
            3)
                echo
                prompt_default "Block Duration (blank=keep)" "" block_duration
                prompt_default "Max IPs (blank=keep)" "" max_ips
                
                if [[ -n "$block_duration" ]] || [[ -n "$max_ips" ]]; then
                    local cmd_args=()
                    [[ -n "$block_duration" ]] && cmd_args+=("--block-duration" "$block_duration")
                    [[ -n "$max_ips" ]] && cmd_args+=("--max-ips" "$max_ips")
                    python3 $CLI_PATH config-ip-limit "${cmd_args[@]}"
                else
                    print_warning "No changes"
                fi
                wait_seconds 2
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

display_main_menu() {
    print_header
    
    # System info in compact format
    echo -e "  ${gray}OS${NC} ${white}$OS${NC}  ${gray}│${NC}  ${gray}ARCH${NC} ${white}$ARCH${NC}"
    echo -e "  ${gray}IP${NC} ${cyan}$IP${NC}  ${gray}│${NC}  ${gray}ISP${NC} ${white}$ISP${NC}"
    echo -e "  ${gray}CPU${NC} ${yellow}$CPU${NC}  ${gray}│${NC}  ${gray}RAM${NC} ${yellow}$RAM${NC}"
    
    print_section "Version Info"
    check_core_version
    check_version
    
    print_section "Services"
    check_services
    
    print_section "Main Menu"
    menu_item "1" "Hysteria2 Menu" "$green"
    menu_item "2" "Advanced Settings" "$cyan"
    menu_item "3" "Update Panel" "$yellow"
    menu_item "0" "Exit" "$red"
    print_line
    echo -ne "\n${IRIDIUM}❯${NC} "
}

main_menu() {
    local choice
    while true; do
        get_system_info
        display_main_menu
        read -n 1 -s choice
        echo
        case $choice in
            1) hysteria2_menu ;;
            2) advance_menu ;;
            3) 
                if confirm "Update Iridium Panel?"; then
                    hysteria_upgrade
                    wait_seconds 3
                fi
                ;;
            0|q) echo -e "\n${IRIDIUM}Goodbye!${NC}\n"; exit 0 ;;
            *) ;;
        esac
    done
}

display_hysteria2_menu() {
    clear
    echo -e "${IRIDIUM}${BOLD}"
    echo '  ╦ ╦╦ ╦╔═╗╔╦╗╔═╗╦═╗╦╔═╗2'
    echo '  ╠═╣╚╦╝╚═╗ ║ ║╣ ╠╦╝║╠═╣ '
    echo '  ╩ ╩ ╩ ╚═╝ ╩ ╚═╝╩╚═╩╩ ╩ '
    echo -e "${NC}"
    
    print_section "User Management"
    menu_item "1" "Install & Configure Hysteria2" "$green"
    menu_item "2" "Add User" "$cyan"
    menu_item "3" "Edit User" "$cyan"
    menu_item "4" "Reset User" "$yellow"
    menu_item "5" "Remove User" "$red"
    menu_item "6" "Get User Info" "$cyan"
    menu_item "7" "List All Users" "$cyan"
    menu_item "8" "Traffic Status" "$cyan"
    menu_item "9" "Show User URI/QR" "$cyan"
    print_line
    menu_item "0" "← Back" "$gray"
    print_line
    echo -ne "\n${IRIDIUM}❯${NC} "
}

hysteria2_menu() {
    local choice
    while true; do
        display_hysteria2_menu
        read -n 1 -s choice
        echo
        case $choice in
            1) hysteria2_install_handler; wait_seconds 2 ;;
            2) hysteria2_add_user_handler; wait_seconds 2 ;;
            3) hysteria2_edit_user_handler; wait_seconds 2 ;;
            4) 
                if confirm "Reset user traffic and stats?"; then
                    hysteria2_reset_user_handler
                    wait_seconds 2
                fi
                ;;
            5) 
                if confirm "Delete user permanently?" "n"; then
                    hysteria2_remove_user_handler
                    wait_seconds 2
                fi
                ;;
            6) hysteria2_get_user_handler; wait_seconds 3 ;;
            7) hysteria2_list_users_handler; wait_seconds 3 ;;
            8) python3 $CLI_PATH traffic-status; wait_seconds 3 ;;
            9) hysteria2_show_user_uri_handler; wait_seconds 3 ;;
            0|q) return ;;
            *) ;;
        esac
    done
}

display_advance_menu() {
    clear
    echo -e "${IRIDIUM}${BOLD}  ⚙  Advanced Settings${NC}\n"
    
    print_section "Installation"
    menu_item "1" "Install TCP Brutal" "$green"
    menu_item "2" "Install WARP" "$green"
    menu_item "3" "Configure WARP" "$cyan"
    menu_item "4" "Uninstall WARP" "$red"
    
    print_section "Services"
    menu_item "5" "Telegram Bot" "$cyan"
    menu_item "6" "Normal-SUB SubLink" "$cyan"
    menu_item "7" "Web Panel" "$cyan"
    menu_item "8" "IP Limiter" "$cyan"
    
    print_section "Hysteria2 Config"
    menu_item "9" "Change Port" "$yellow"
    menu_item "a" "Change SNI" "$yellow"
    menu_item "b" "Manage OBFS" "$yellow"
    menu_item "c" "Change IPs" "$yellow"
    menu_item "d" "Update Geo Files" "$yellow"
    menu_item "e" "Manage Masquerade" "$yellow"
    
    print_section "System"
    menu_item "r" "Restart Hysteria2" "$cyan"
    menu_item "u" "Update Hysteria2 Core" "$cyan"
    menu_item "x" "Uninstall Hysteria2" "$red"
    print_line
    menu_item "0" "← Back" "$gray"
    print_line
    echo -ne "\n${IRIDIUM}❯${NC} "
}

advance_menu() {
    local choice
    while true; do
        display_advance_menu
        read -n 1 -s choice
        echo
        case $choice in
            1) python3 $CLI_PATH install-tcp-brutal; wait_seconds 2 ;;
            2) python3 $CLI_PATH install-warp; wait_seconds 2 ;;
            3) warp_configure_handler ;;
            4) 
                if confirm "Uninstall WARP?" "n"; then
                    python3 $CLI_PATH uninstall-warp
                    wait_seconds 2
                fi
                ;;
            5) telegram_bot_handler ;;
            6) normalsub_handler ;;
            7) webpanel_handler ;;
            8) ip_limit_handler ;;
            9) hysteria2_change_port_handler; wait_seconds 2 ;;
            a|A) hysteria2_change_sni_handler; wait_seconds 2 ;;
            b|B) obfs_handler ;;
            c|C) edit_ips ;;
            d|D) geo_update_handler; wait_seconds 2 ;;
            e|E) masquerade_handler ;;
            r|R) 
                if confirm "Restart Hysteria2?"; then
                    python3 $CLI_PATH restart-hysteria2
                    wait_seconds 2
                fi
                ;;
            u|U) 
                if confirm "Update Hysteria2 Core?"; then
                    python3 $CLI_PATH update-hysteria2
                    wait_seconds 2
                fi
                ;;
            x|X) 
                if confirm "Uninstall Hysteria2? This action is irreversible!" "n"; then
                    python3 $CLI_PATH uninstall-hysteria2
                    wait_seconds 2
                fi
                ;;
            0|q) return ;;
            *) ;;
        esac
    done
}
define_colors
main_menu