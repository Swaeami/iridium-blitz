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
        echo "======================================"
        echo "      IP/Domain Address Manager      "
        echo "======================================"
        echo "1. Change IPv4 or Domain"
        echo "2. Change IPv6 or Domain"
        echo "0. Back"
        echo "======================================"
        read -p "Enter your choice [0-2]: " choice

        case $choice in
            1)
                read -p "Enter the new IPv4 address or domain: " new_ip4_or_domain
                if [[ $new_ip4_or_domain =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
                    if [[ $(echo "$new_ip4_or_domain" | awk -F. '{for (i=1;i<=NF;i++) if ($i>255) exit 1}') ]]; then
                        echo "Error: Invalid IPv4 address. Values must be between 0 and 255."
                    else
                        python3 "$CLI_PATH" ip-address --edit -4 "$new_ip4_or_domain"
                        echo "IPv4 address has been updated to $new_ip4_or_domain."
                    fi
                elif [[ $new_ip4_or_domain =~ ^[a-zA-Z0-9.-]+$ ]] && [[ ! $new_ip4_or_domain =~ [/:] ]]; then
                    python3 "$CLI_PATH" ip-address --edit -4 "$new_ip4_or_domain"
                    echo "Domain has been updated to $new_ip4_or_domain."
                else
                    echo "Error: Invalid IPv4 or domain format."
                fi
                break
                ;;
            2)
                read -p "Enter the new IPv6 address or domain: " new_ip6_or_domain
                if [[ $new_ip6_or_domain =~ ^(([0-9a-fA-F]{1,4}:){7}([0-9a-fA-F]{1,4}|:)|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:))$ ]]; then
                    python3 "$CLI_PATH" ip-address --edit -6 "$new_ip6_or_domain"
                    echo "IPv6 address has been updated to $new_ip6_or_domain."
                elif [[ $new_ip6_or_domain =~ ^[a-zA-Z0-9.-]+$ ]] && [[ ! $new_ip6_or_domain =~ [/:] ]]; then
                    python3 "$CLI_PATH" ip-address --edit -6 "$new_ip6_or_domain"
                    echo "Domain has been updated to $new_ip6_or_domain."
                else
                    echo "Error: Invalid IPv6 or domain format."
                fi
                break
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                break
                ;;
        esac
        echo "======================================"
        read -p "Press Enter to continue..."
    done
}

hysteria_upgrade(){
    bash <(curl https://raw.githubusercontent.com/Swaeami/iridium-blitz/main/upgrade.sh)
}

warp_configure_handler() {
    local service_name="wg-quick@wgcf.service"

    if systemctl is-active --quiet "$service_name"; then
        echo -e "${cyan}=== WARP Status ===${NC}"
        status_json=$(python3 $CLI_PATH warp-status)

        all_traffic=$(echo "$status_json" | grep -o '"all_traffic_via_warp": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        popular_sites=$(echo "$status_json" | grep -o '"popular_sites_via_warp": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        domestic_sites_via_warp=$(echo "$status_json" | grep -o '"domestic_sites_via_warp": *[^,}]*' | cut -d':' -f2 | tr -d ' "')
        block_adult=$(echo "$status_json" | grep -o '"block_adult_content": *[^,}]*' | cut -d':' -f2 | tr -d ' "')

        display_status() {
            local label="$1"
            local status_val="$2"
            if [ "$status_val" = "true" ]; then
                echo -e "  ${green}✓${NC} $label: ${green}Enabled${NC}"
            else
                echo -e "  ${red}✗${NC} $label: ${red}Disabled${NC}"
            fi
        }

        display_status "All Traffic via WARP" "$all_traffic"
        display_status "Popular Sites via WARP" "$popular_sites"
        display_status "Domestic Sites via WARP" "$domestic_sites_via_warp"
        display_status "Block Adult Content" "$block_adult"

        echo -e "${cyan}==================${NC}"
        echo

        echo "Configure WARP Options (Toggle):"
        echo "1. All traffic via WARP"
        echo "2. Popular sites via WARP"
        echo "3. Domestic sites (WARP/Reject)"
        echo "4. Block adult content"
        echo "5. WARP Status Profile (IP etc.)"
        echo "6. Change WARP IP address"
        echo "7. Switch to WARP Plus"
        echo "8. Switch to Normal WARP"
        echo "0. Cancel"

        read -p "Select an option to toggle: " option

        case $option in
            1)
                target_state=$([ "$all_traffic" = "true" ] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-all "$target_state" ;;
            2)
                target_state=$([ "$popular_sites" = "true" ] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-popular-sites "$target_state" ;;
            3)
                target_state=$([ "$domestic_sites_via_warp" = "true" ] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-domestic-sites "$target_state" ;;
            4)
                target_state=$([ "$block_adult" = "true" ] && echo "off" || echo "on")
                python3 $CLI_PATH configure-warp --set-block-adult-sites "$target_state" ;;
            5)
                current_ip=$(python3 $CLI_PATH warp-status | grep -o '"ip": *"[^"]*"' | cut -d':' -f2- | tr -d '" ')
                if [ -z "$current_ip" ]; then
                    current_ip=$(curl -s --interface wgcf --connect-timeout 1 http://v4.ident.me || echo "N/A")
                fi
                cd /etc/warp/ && wgcf status
                echo
                echo -e "${yellow}Warp IP:${NC} ${cyan}${current_ip}${NC}"
                ;;
            6)
                old_ip=$(curl -s --interface wgcf --connect-timeout 1 http://v4.ident.me || echo "N/A")
                echo -e "${yellow}Current IP:${NC} ${cyan}$old_ip${NC}"
                echo "Restarting $service_name to attempt IP change..."
                systemctl restart "$service_name"

                echo -n "Waiting for service to restart"
                for i in {1..5}; do
                    echo -n "."
                    sleep 1
                done
                echo

                new_ip=$(curl -s --interface wgcf --connect-timeout 1 http://v4.ident.me || echo "N/A")
                echo -e "${yellow}New IP:${NC} ${green}$new_ip${NC}"

                if [ "$old_ip" != "N/A" ] && [ "$new_ip" != "N/A" ] && [ "$old_ip" != "$new_ip" ]; then
                    echo -e "${green}✓ IP address changed successfully${NC}"
                elif [ "$old_ip" = "$new_ip" ] && [ "$old_ip" != "N/A" ]; then
                    echo -e "${yellow}⚠ IP address remained the same${NC}"
                else
                    echo -e "${red}✗ Could not verify IP change.${NC}"
                fi
                ;;
            7)
                echo -e "${yellow}Switching to WARP Plus...${NC}"
                read -p "Enter your WARP Plus license key: " warp_key

                if [ -z "$warp_key" ]; then
                    echo -e "${red}Error: WARP Plus key is required.${NC}"
                else
                    echo "Stopping WARP service..."
                    systemctl stop "$service_name" 2>/dev/null

                    cd /etc/warp/ || { echo -e "${red}Failed to change directory to /etc/warp/${NC}"; return 1; }

                    echo "Updating WARP Plus configuration..."
                    WGCF_LICENSE_KEY="$warp_key" wgcf update

                    if [ $? -eq 0 ]; then
                        echo "Starting WARP service..."
                        systemctl start "$service_name"
                        echo -e "${green}✓ Successfully switched to WARP Plus${NC}"
                        python3 "$CLI_PATH" restart-hysteria2 > /dev/null 2>&1
                    else
                        echo -e "${red}✗ Failed to update WARP Plus configuration${NC}"
                        systemctl start "$service_name"
                    fi
                fi
                ;;
            8)
                echo -e "${yellow}Switching to Normal WARP...${NC}"
                echo "This will create a new WARP account. Continue? (y/N)"
                read -p "" confirm

                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    echo "Stopping WARP service..."
                    systemctl stop "$service_name" 2>/dev/null

                    cd /etc/warp/ || { echo -e "${red}Failed to change directory to /etc/warp/${NC}"; return 1; }

                    echo "Creating new WARP account..."
                    rm -f wgcf-account.toml
                    yes | wgcf register

                    if [ $? -eq 0 ]; then
                        echo "Starting WARP service..."
                        systemctl start "$service_name"
                        echo -e "${green}✓ Successfully switched to Normal WARP with new account${NC}"
                        python3 "$CLI_PATH" restart-hysteria2 > /dev/null 2>&1
                    else
                        echo -e "${red}✗ Failed to register new WARP account${NC}"
                        systemctl start "$service_name"
                    fi
                else
                    echo -e "${yellow}Operation canceled${NC}"
                fi
                ;;
            0) echo "WARP configuration canceled." ;;
            *) echo -e "${red}Invalid option. Please try again.${NC}" ;;
        esac

    else
        echo -e "${red}$service_name is not active. Please start the service before configuring WARP.${NC}"
    fi
}

telegram_bot_handler() {
    while true; do
        echo -e "${cyan}1.${NC} Start Telegram bot service"
        echo -e "${red}2.${NC} Stop Telegram bot service"
        echo "0. Back"
        read -p "Choose an option: " option

        case $option in
            1)
                if systemctl is-active --quiet hysteria-telegram-bot.service; then
                    echo "The hysteria-telegram-bot.service is already active."
                else
                    while true; do
                        read -e -p "Enter the Telegram bot token: " token
                        if [ -z "$token" ]; then
                            echo "Token cannot be empty. Please try again."
                        else
                            break
                        fi
                    done

                    while true; do
                        read -e -p "Enter the admin IDs (comma-separated): " admin_ids
                        if [[ ! "$admin_ids" =~ ^[0-9,]+$ ]]; then
                            echo "Admin IDs can only contain numbers and commas. Please try again."
                        elif [ -z "$admin_ids" ]; then
                            echo "Admin IDs cannot be empty. Please try again."
                        else
                            break
                        fi
                    done

                    python3 $CLI_PATH telegram -a start -t "$token" -aid "$admin_ids"
                fi
                ;;
            2)
                python3 $CLI_PATH telegram -a stop
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

singbox_handler() {
    echo -e "${red} Deprecated${NC}"
}

normalsub_handler() {
    while true; do
        echo -e "${cyan}1.${NC} Start Normal-Sub service"
        echo -e "${red}2.${NC} Stop Normal-Sub service"
        echo -e "${yellow}3.${NC} Change SUBPATH"
        echo "0. Back"
        read -p "Choose an option: " option

        case $option in
            1)
                if systemctl is-active --quiet hysteria-normal-sub.service; then
                    echo "The hysteria-normal-sub.service is already active."
                else
                    while true; do
                        read -e -p "Enter the domain name for the SSL certificate: " domain
                        if [ -z "$domain" ]; then
                            echo "Domain name cannot be empty. Please try again."
                        else
                            break
                        fi
                    done

                    while true; do
                        read -e -p "Enter the port number for the service: " port
                        if [ -z "$port" ]; then
                            echo "Port number cannot be empty. Please try again."
                        elif ! [[ "$port" =~ ^[0-9]+$ ]]; then
                            echo "Port must be a number. Please try again."
                        else
                            break
                        fi
                    done

                    python3 $CLI_PATH normal-sub -a start -d "$domain" -p "$port"
                fi
                ;;
            2)
                if ! systemctl is-active --quiet hysteria-normal-sub.service; then
                    echo "The hysteria-normal-sub.service is already inactive."
                else
                    python3 $CLI_PATH normal-sub -a stop
                fi
                ;;
            3)
                if ! systemctl is-active --quiet hysteria-normal-sub.service; then
                    echo "Error: The hysteria-normal-sub.service is not active. Start the service first."
                    continue
                fi

                while true; do
                    read -e -p "Enter new SUBPATH (Must include Uppercase, Lowercase, and Numbers): " subpath
                    if [[ -z "$subpath" ]]; then
                        echo "Error: SUBPATH cannot be empty. Please try again."
                    elif ! [[ "$subpath" =~ [A-Z] ]] || ! [[ "$subpath" =~ [a-z] ]] || ! [[ "$subpath" =~ [0-9] ]]; then
                        echo "Error: SUBPATH must include at least one uppercase letter, one lowercase letter, and one number."
                    else
                        python3 $CLI_PATH normal-sub -a edit_subpath -sp "$subpath"
                        break
                    fi
                done
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

webpanel_handler() {
    service_status=$(python3 "$CLI_PATH" get-webpanel-services-status)
    echo -e "${cyan}Services Status:${NC}"
    echo "$service_status"
    echo ""

    while true; do
        echo -e "${cyan}1.${NC} Start WebPanel service"
        echo -e "${red}2.${NC} Stop WebPanel service"
        echo -e "${cyan}3.${NC} Get WebPanel URL"
        echo -e "${cyan}4.${NC} Show API Token"
        echo -e "${yellow}5.${NC} Reset WebPanel Credentials"
        echo -e "${yellow}6.${NC} Change Domain/Port"
        echo -e "${yellow}7.${NC} Change Root Path"
        echo -e "${yellow}8.${NC} Change Session Expiration"
        echo "0. Back"
        read -p "Choose an option: " option

        case $option in
            1)
                if systemctl is-active --quiet hysteria-webpanel.service; then
                    echo "The hysteria-webpanel.service is already active."
                else
                    while true; do
                        read -e -p "Enter the domain name for the SSL certificate: " domain
                        if [ -z "$domain" ]; then
                            echo "Domain name cannot be empty. Please try again."
                        else
                            break
                        fi
                    done

                    while true; do
                        read -e -p "Enter the port number for the service: " port
                        if [ -z "$port" ]; then
                            echo "Port number cannot be empty. Please try again."
                        elif ! [[ "$port" =~ ^[0-9]+$ ]]; then
                            echo "Port must be a number. Please try again."
                        else
                            break
                        fi
                    done

                    while true; do
                        read -e -p "Enter the admin username: " admin_username
                        if [ -z "$admin_username" ]; then
                            echo "Admin username cannot be empty. Please try again."
                        else
                            break
                        fi
                    done

                    while true; do
                        read -sp "Enter the admin password: " admin_password
                        echo ""
                        if [ -z "$admin_password" ]; then
                            echo "Admin password cannot be empty. Please try again."
                            continue
                        fi
                        local check_password
                        read -sp "Enter the admin password again: " check_password
                        echo ""
                        if [ -z "$check_password" ]; then
                            echo "Admin password cannot be empty. Please try again."
                            continue
                        fi
                        if [ "$check_password" == "$admin_password" ]; then
                            echo "Password is set!"
                            break
                        fi
                        echo "Passwords did NOT match. Please try again."
                    done

                    python3 $CLI_PATH webpanel -a start -d "$domain" -p "$port" -au "$admin_username" -ap "$admin_password"
                fi
                ;;
            2)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                    echo "The hysteria-webpanel.service is already inactive."
                else
                    python3 $CLI_PATH webpanel -a stop
                fi
                ;;
            3)
                url=$(python3 $CLI_PATH get-webpanel-url)
                echo "-------------------------------"
                echo "$url"
                echo "-------------------------------"
                ;;
            4)
                api_token=$(python3 $CLI_PATH get-webpanel-api-token)
                echo "-------------------------------"
                echo "$api_token"
                echo "-------------------------------"
                ;;
            5)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                     echo -e "${red}WebPanel service is not running. Cannot reset credentials.${NC}"
                else
                    read -e -p "Enter new admin username (leave blank to keep current): " new_username
                    read -e -p "Enter new admin password (leave blank to keep current): " new_password
                    echo

                    if [ -z "$new_username" ] && [ -z "$new_password" ]; then
                        echo -e "${yellow}No changes specified. Aborting.${NC}"
                    else
                        local cmd_args=("-u" "$new_username")
                        if [ -n "$new_password" ]; then
                             cmd_args+=("-p" "$new_password")
                        fi

                        if [ -z "$new_username" ]; then
                             cmd_args=()
                             if [ -n "$new_password" ]; then
                                cmd_args+=("-p" "$new_password")
                             fi
                        fi

                        echo "Attempting to reset credentials..."
                        python3 "$CLI_PATH" reset-webpanel-creds "${cmd_args[@]}"
                    fi
                fi
                ;;
            6)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                     echo -e "${red}WebPanel service is not running. Cannot perform this action.${NC}"
                else
                    read -e -p "Enter new domain (leave blank to keep current): " new_domain
                    read -e -p "Enter new port (leave blank to keep current): " new_port

                    if [ -z "$new_domain" ] && [ -z "$new_port" ]; then
                        echo -e "${yellow}No changes specified. Aborting.${NC}"
                    else
                        local cmd_args=()
                        if [ -n "$new_domain" ]; then
                             cmd_args+=("--domain" "$new_domain")
                        fi
                        if [ -n "$new_port" ]; then
                             cmd_args+=("--port" "$new_port")
                        fi
                        echo "Attempting to change domain/port..."
                        python3 "$CLI_PATH" change-webpanel-domain-port "${cmd_args[@]}"
                    fi
                fi
                ;;
            7)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                     echo -e "${red}WebPanel service is not running. Cannot perform this action.${NC}"
                else
                    read -e -p "Enter new root path (leave blank for random): " new_root_path
                    local cmd_args=()
                    if [ -n "$new_root_path" ]; then
                        cmd_args+=("--path" "$new_root_path")
                    fi
                    echo "Attempting to change root path..."
                    python3 "$CLI_PATH" change-webpanel-root "${cmd_args[@]}"
                fi
                ;;
            8)
                if ! systemctl is-active --quiet hysteria-webpanel.service; then
                     echo -e "${red}WebPanel service is not running. Cannot perform this action.${NC}"
                else
                    while true; do
                        read -e -p "Enter new session expiration in minutes: " new_minutes
                        if [[ "$new_minutes" =~ ^[0-9]+$ ]]; then
                            break
                        else
                            echo -e "${red}Error:${NC} Please enter a valid number."
                        fi
                    done
                    echo "Attempting to change session expiration..."
                    python3 "$CLI_PATH" change-webpanel-exp --minutes "$new_minutes"
                fi
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

obfs_handler() {
    while true; do
        echo -e "${cyan}1.${NC} Remove Obfs"
        echo -e "${red}2.${NC} Generating new Obfs"
        echo "0. Back"
        read -p "Choose an option: " option

        case $option in
            1)
                python3 $CLI_PATH manage_obfs -r
                ;;
            2)
                status=$(python3 $CLI_PATH masquerade -s)
                if [[ "$status" == "Enabled" ]]; then
                    echo -e "${red}Error:${NC} Cannot use Obfs when masquerade is enabled."
                else
                    python3 $CLI_PATH manage_obfs -g
                fi
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

geo_update_handler() {
    echo "Configure Geo Update Options:"
    echo "1. Update Iran Geo Files"
    echo "2. Update China Geo Files"
    echo "3. Update Russia Geo Files"
    echo "4. Check Current Geo Files"
    echo "0. Cancel"

    read -p "Select an option: " option

    case $option in
        1)
            echo "Updating Iran Geo Files..."
            python3 $CLI_PATH update-geo --country iran
            ;;
        2)
            echo "Updating China Geo Files..."
            python3 $CLI_PATH update-geo --country china
            ;;
        3)
            echo "Updating Russia Geo Files..."
            python3 $CLI_PATH update-geo --country russia
            ;;
        4)
            echo "Current Geo Files Information:"
            echo "--------------------------"
            if [ -f "/etc/hysteria/geosite.dat" ]; then
                echo "GeoSite File:"
                ls -lh /etc/hysteria/geosite.dat
                echo "Last modified: $(stat -c %y /etc/hysteria/geosite.dat)"
            else
                echo "GeoSite file not found!"
            fi
            echo
            if [ -f "/etc/hysteria/geoip.dat" ]; then
                echo "GeoIP File:"
                ls -lh /etc/hysteria/geoip.dat
                echo "Last modified: $(stat -c %y /etc/hysteria/geoip.dat)"
            else
                echo "GeoIP file not found!"
            fi
            ;;
        0)
            echo "Geo update configuration canceled."
            ;;
        *)
            echo "Invalid option. Please try again."
            ;;
    esac
}

masquerade_handler() {
    while true; do
        status=$(python3 $CLI_PATH masquerade -s)

        echo "--------------------------"
        if [ "$status" == "Enabled" ]; then
            echo -e "Masquerade Status: ${green}${status}${NC}"
        else
            echo -e "Masquerade Status: ${red}${status}${NC}"
        fi
        echo "--------------------------"

        echo -e "${cyan}1.${NC} Enable Masquerade"
        echo -e "${cyan}2.${NC} Remove Masquerade"
        echo "0. Back"
        read -p "Choose an option: " option

        case $option in
            1)
                obfs_status=$(python3 $CLI_PATH manage_obfs --check 2>/dev/null)
                if [[ "$obfs_status" == "OBFS is active." ]]; then
                    echo -e "${red}Error:${NC} Cannot enable Masquerade while OBFS is active. Please disable OBFS first."
                else
                    python3 $CLI_PATH masquerade -e
                fi
                ;;
            2)
                python3 $CLI_PATH masquerade -r
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

ip_limit_handler() {
    while true; do
        echo -e "${cyan}1.${NC} Start IP Limiter Service"
        echo -e "${red}2.${NC} Stop IP Limiter Service"
        echo -e "${yellow}3.${NC} Change IP Limiter Configuration"
        echo "0. Back"
        read -p "Choose an option: " option

        case $option in
            1)
                if systemctl is-active --quiet hysteria-ip-limit.service; then
                    echo "The hysteria-ip-limit.service is already active."
                else
                    while true; do
                        read -e -p "Enter Block Duration (seconds, default: 60): " block_duration
                        block_duration=${block_duration:-60}
                        if ! [[ "$block_duration" =~ ^[0-9]+$ ]]; then
                            echo "Invalid Block Duration. Please enter a number."
                        else
                            break
                        fi
                    done

                    while true; do
                        read -e -p "Enter Max IPs per User (default: 1): " max_ips
                        max_ips=${max_ips:-1}
                        if ! [[ "$max_ips" =~ ^[0-9]+$ ]]; then
                            echo "Invalid Max IPs. Please enter a number."
                        else
                            break
                        fi
                    done
                    python3 $CLI_PATH config-ip-limit --block-duration "$block_duration" --max-ips "$max_ips"
                    python3 $CLI_PATH start-ip-limit
                fi
                ;;
            2)
                if ! systemctl is-active --quiet hysteria-ip-limit.service; then
                    echo "The hysteria-ip-limit.service is already inactive."
                else
                    python3 $CLI_PATH stop-ip-limit
                fi
                ;;
            3)
                block_duration=""
                max_ips=""
                updated=false

                while true; do
                    read -e -p "Enter New Block Duration (seconds, current: $(grep '^BLOCK_DURATION=' /etc/hysteria/.configs.env | cut -d'=' -f2), leave empty to keep current): " input_block_duration
                    if [[ -n "$input_block_duration" ]] && ! [[ "$input_block_duration" =~ ^[0-9]+$ ]]; then
                        echo "Invalid Block Duration. Please enter a number or leave empty."
                    else
                        if [[ -n "$input_block_duration" ]]; then
                            block_duration="$input_block_duration"
                            updated=true
                        fi
                        break
                    fi
                done

                while true; do
                    read -e -p "Enter New Max IPs per User (current: $(grep '^MAX_IPS=' /etc/hysteria/.configs.env | cut -d'=' -f2), leave empty to keep current): " input_max_ips
                    if [[ -n "$input_max_ips" ]] && ! [[ "$input_max_ips" =~ ^[0-9]+$ ]]; then
                        echo "Invalid Max IPs. Please enter a number or leave empty."
                    else
                        if [[ -n "$input_max_ips" ]]; then
                            max_ips="$input_max_ips"
                            updated=true
                        fi
                        break
                    fi
                done

                if [[ "$updated" == "true" ]]; then
                    python3 $CLI_PATH config-ip-limit --block-duration "$block_duration" --max-ips "$max_ips"
                else
                    echo "No changes to IP Limiter configuration were provided."
                fi
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac
    done
}

manage_tariffs_menu() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  📋 Manage Tariffs${NC}\n"
        
        # List tariffs
        echo -e "${gray}Current Tariffs:${NC}"
        python3 $CLI_PATH tariff list 2>/dev/null || echo "  No tariffs found"
        echo ""
        
        print_section "Actions"
        echo -e "${green}1.${NC} Add New Tariff"
        echo -e "${yellow}2.${NC} Delete Tariff"
        echo -e "${cyan}3.${NC} Refresh List"
        print_line
        echo "0. Back"
        print_line
        read -p "Choose an option: " option

        case $option in
            1)
                echo ""
                read -e -p "Tariff Name (e.g. 'VPN Premium'): " name
                if [ -z "$name" ]; then
                    echo "Name cannot be empty."
                    read -p "Press Enter..."
                    continue
                fi
                echo "Tariff Type:"
                echo "  1) Unlimited traffic (time-based)"
                echo "  2) Limited traffic"
                read -e -p "Choose type [1/2]: " type_choice
                if [ "$type_choice" = "2" ]; then
                    tariff_type="traffic"
                    read -e -p "Traffic limit (GB): " traffic_gb
                else
                    tariff_type="time"
                    traffic_gb=""
                fi
                echo ""
                echo "Enter prices in Telegram Stars:"
                read -e -p "1 month price ⭐: " price_1m
                read -e -p "3 months price ⭐ (optional): " price_3m
                read -e -p "6 months price ⭐ (optional): " price_6m
                read -e -p "12 months price ⭐ (optional): " price_12m
                
                if [ -z "$price_1m" ]; then
                    echo "Price for 1 month is required."
                    read -p "Press Enter..."
                    continue
                fi
                
                # Use default price for legacy compatibility
                cmd="python3 $CLI_PATH tariff add -n '$name' -t $tariff_type -p 0 --price-stars $price_1m"
                [ -n "$traffic_gb" ] && cmd="$cmd --traffic-gb $traffic_gb"
                eval $cmd
                echo ""
                read -p "Press Enter to continue..."
                ;;
            2)
                echo ""
                read -e -p "Enter Tariff ID to delete: " tariff_id
                if [ -n "$tariff_id" ]; then
                    read -p "Are you sure? (y/n): " confirm
                    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                        python3 $CLI_PATH tariff delete -i "$tariff_id"
                    fi
                fi
                read -p "Press Enter to continue..."
                ;;
            3)
                # Just refresh - loop will re-display
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option."
                sleep 1
                ;;
        esac
    done
}

manage_promos_menu() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🎁 Manage Promo Codes${NC}\n"
        
        # List promos
        echo -e "${gray}Current Promo Codes:${NC}"
        python3 $CLI_PATH promo list 2>/dev/null || echo "  No promo codes found"
        echo ""
        
        print_section "Actions"
        echo -e "${green}1.${NC} Add New Promo Code"
        echo -e "${red}2.${NC} Delete Promo Code"
        echo -e "${cyan}3.${NC} Refresh List"
        print_line
        echo "0. Back"
        print_line
        read -p "Choose an option: " option

        case $option in
            1)
                echo ""
                read -e -p "Promo Code (leave empty for auto): " code
                echo "Promo Type:"
                echo "  1) Discount (%)"
                echo "  2) Free Period (days)"
                echo "  3) Extra Traffic (GB)"
                read -e -p "Choose type [1/2/3]: " ptype
                case $ptype in
                    1) 
                        promo_type="discount"
                        read -e -p "Discount percentage (1-100): " value
                        ;;
                    2) 
                        promo_type="free_period"
                        read -e -p "Free days: " value
                        ;;
                    3) 
                        promo_type="extra_traffic"
                        read -e -p "Extra traffic (GB): " value
                        ;;
                    *) 
                        echo "Invalid type"
                        read -p "Press Enter..."
                        continue
                        ;;
                esac
                read -e -p "Max Uses (default: 100): " max_uses
                max_uses=${max_uses:-100}
                read -e -p "Expire in days (0 = never): " expire
                
                cmd="python3 $CLI_PATH promo add -t $promo_type -v $value -m $max_uses"
                [ -n "$code" ] && cmd="$cmd -c '$code'"
                [ -n "$expire" ] && [ "$expire" != "0" ] && cmd="$cmd -e $expire"
                eval $cmd
                echo ""
                read -p "Press Enter to continue..."
                ;;
            2)
                echo ""
                read -e -p "Enter Promo Code to delete: " promo_code
                if [ -n "$promo_code" ]; then
                    read -p "Are you sure? (y/n): " confirm
                    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                        python3 $CLI_PATH promo delete -c "$promo_code"
                    fi
                fi
                read -p "Press Enter to continue..."
                ;;
            3)
                # Just refresh - loop will re-display
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option."
                sleep 1
                ;;
        esac
    done
}

client_bot_handler() {
    while true; do
        clear
        echo -e "${IRIDIUM}${BOLD}  🏪 Client Bot (Sales)${NC}\n"
        print_section "Service"
        echo -e "${cyan}1.${NC} Start Client Bot"
        echo -e "${red}2.${NC} Stop Client Bot"
        echo -e "${yellow}3.${NC} Restart Client Bot"
        echo -e "${cyan}4.${NC} Check Status"
        print_section "Management"
        echo -e "${green}5.${NC} Manage Tariffs"
        echo -e "${green}6.${NC} Manage Promo Codes"
        echo -e "${cyan}7.${NC} Shop Statistics"
        print_line
        echo "0. Back"
        print_line
        read -p "Choose an option: " option

        case $option in
            1)
                if systemctl is-active --quiet hysteria-client-bot.service; then
                    echo "Client bot is already running."
                else
                    read -e -p "Enter Bot Token: " token
                    if [ -z "$token" ]; then
                        echo "Token cannot be empty."
                        continue
                    fi
                    read -e -p "Support Username (optional, e.g. @admin): " support
                    read -e -p "Trial Days (default: 3): " trial_days
                    trial_days=${trial_days:-3}
                    read -e -p "Trial Traffic GB (default: 999999): " trial_traffic
                    trial_traffic=${trial_traffic:-999999}
                    
                    python3 $CLI_PATH client-bot start -t "$token" \
                        --support "$support" \
                        --trial-days "$trial_days" \
                        --trial-traffic "$trial_traffic"
                fi
                wait_seconds 2
                ;;
            2)
                python3 $CLI_PATH client-bot stop
                wait_seconds 2
                ;;
            3)
                python3 $CLI_PATH client-bot restart
                wait_seconds 2
                ;;
            4)
                python3 $CLI_PATH client-bot status
                read -p "Press Enter to continue..."
                ;;
            5)
                manage_tariffs_menu
                ;;
            6)
                manage_promos_menu
                ;;
            7)
                python3 $CLI_PATH shop-stats
                read -p "Press Enter to continue..."
                ;;
            0)
                break
                ;;
            *)
                echo "Invalid option."
                ;;
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
        read -r choice
        case $choice in
            1) hysteria2_menu ;;
            2) advance_menu ;;
            3) hysteria_upgrade ;;
            0) echo -e "\n${IRIDIUM}Goodbye!${NC}\n"; exit 0 ;;
            *) print_error "Invalid option"; sleep 1 ;;
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
        read -r choice
        case $choice in
            1) hysteria2_install_handler; wait_seconds 2 ;;
            2) hysteria2_add_user_handler; wait_seconds 2 ;;
            3) hysteria2_edit_user_handler; wait_seconds 2 ;;
            4) hysteria2_reset_user_handler; wait_seconds 2 ;;
            5) hysteria2_remove_user_handler; wait_seconds 2 ;;
            6) hysteria2_get_user_handler; wait_seconds 3 ;;
            7) hysteria2_list_users_handler; wait_seconds 3 ;;
            8) python3 $CLI_PATH traffic-status; wait_seconds 3 ;;
            9) hysteria2_show_user_uri_handler; wait_seconds 3 ;;
            0) return ;;
            *) print_error "Invalid option"; sleep 1 ;;
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
    menu_item "5" "Telegram Bot (Admin)" "$cyan"
    menu_item "6" "Client Bot (Sales)" "$purple"
    menu_item "7" "Normal-SUB SubLink" "$cyan"
    menu_item "8" "Web Panel" "$cyan"
    menu_item "9" "IP Limiter" "$cyan"
    
    print_section "Hysteria2 Config"
    menu_item "a" "Change Port" "$yellow"
    menu_item "b" "Change SNI" "$yellow"
    menu_item "c" "Manage OBFS" "$yellow"
    menu_item "d" "Change IPs" "$yellow"
    menu_item "e" "Update Geo Files" "$yellow"
    menu_item "f" "Manage Masquerade" "$yellow"
    
    print_section "System"
    menu_item "g" "Restart Hysteria2" "$cyan"
    menu_item "h" "Update Hysteria2 Core" "$cyan"
    menu_item "i" "Uninstall Hysteria2" "$red"
    print_line
    menu_item "0" "← Back" "$gray"
    print_line
    echo -ne "\n${IRIDIUM}❯${NC} "
}

advance_menu() {
    local choice
    while true; do
        display_advance_menu
        read -r choice
        case $choice in
            1) python3 $CLI_PATH install-tcp-brutal; wait_seconds 2 ;;
            2) python3 $CLI_PATH install-warp; wait_seconds 2 ;;
            3) warp_configure_handler ;;
            4) python3 $CLI_PATH uninstall-warp; wait_seconds 2 ;;
            5) telegram_bot_handler ;;
            6) client_bot_handler ;;
            7) normalsub_handler ;;
            8) webpanel_handler ;;
            9) ip_limit_handler ;;
            a|A) hysteria2_change_port_handler; wait_seconds 2 ;;
            b|B) hysteria2_change_sni_handler; wait_seconds 2 ;;
            c|C) obfs_handler ;;
            d|D) edit_ips ;;
            e|E) geo_update_handler; wait_seconds 2 ;;
            f|F) masquerade_handler ;;
            g|G) python3 $CLI_PATH restart-hysteria2; wait_seconds 2 ;;
            h|H) python3 $CLI_PATH update-hysteria2; wait_seconds 2 ;;
            i|I) python3 $CLI_PATH uninstall-hysteria2; wait_seconds 2 ;;
            0) return ;;
            *) print_error "Invalid option"; sleep 1 ;;
        esac
    done
}
define_colors
main_menu