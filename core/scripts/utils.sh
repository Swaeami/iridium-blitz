source /etc/hysteria/core/scripts/path.sh

define_colors() {
    # Basic colors
    green='\033[0;32m'
    cyan='\033[0;36m'
    red='\033[0;31m'
    yellow='\033[0;33m'
    blue='\033[0;34m'
    magenta='\033[0;35m'
    white='\033[1;37m'
    gray='\033[0;90m'
    
    # Bold colors
    BOLD='\033[1m'
    DIM='\033[2m'
    
    # Brand colors
    LPurple='\033[1;35m'
    IRIDIUM='\033[38;5;141m'  # Purple/violet for Iridium brand
    ACCENT='\033[38;5;213m'   # Pink accent
    
    NC='\033[0m' # No Color
}

# UI Helper Functions
print_header() {
    clear
    echo -e "${IRIDIUM}"
    echo '  ██╗██████╗ ██╗██████╗ ██╗██╗   ██╗███╗   ███╗'
    echo '  ██║██╔══██╗██║██╔══██╗██║██║   ██║████╗ ████║'
    echo '  ██║██████╔╝██║██║  ██║██║██║   ██║██╔████╔██║'
    echo '  ██║██╔══██╗██║██║  ██║██║██║   ██║██║╚██╔╝██║'
    echo '  ██║██║  ██║██║██████╔╝██║╚██████╔╝██║ ╚═╝ ██║'
    echo '  ╚═╝╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝ ╚═════╝ ╚═╝     ╚═╝'
    echo -e "${NC}"
}

print_line() {
    echo -e "${gray}────────────────────────────────────────────────${NC}"
}

print_section() {
    local title="$1"
    echo -e "\n${IRIDIUM}▸ ${BOLD}${title}${NC}"
    print_line
}

print_success() {
    echo -e "${green}✓${NC} $1"
}

print_error() {
    echo -e "${red}✗${NC} $1"
}

print_warning() {
    echo -e "${yellow}!${NC} $1"
}

print_info() {
    echo -e "${cyan}ℹ${NC} $1"
}

# Menu item formatter
menu_item() {
    local num="$1"
    local text="$2"
    local color="${3:-$cyan}"
    printf "  ${color}[${white}%2s${color}]${NC} %s\n" "$num" "$text"
}

# Status badge
status_badge() {
    local status="$1"
    if [ "$status" = "active" ] || [ "$status" = "running" ]; then
        echo -e "${green}●${NC}"
    else
        echo -e "${red}●${NC}"
    fi
}

# Progress spinner
spin() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while kill -0 $pid 2>/dev/null; do
        local temp=${spinstr#?}
        printf " ${IRIDIUM}%c${NC}" "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b"
    done
    printf "  \b\b"
}

# Prompt with default value
prompt_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$(echo -e "${IRIDIUM}?${NC} ${prompt} [${cyan}${default}${NC}]: ")" input
        eval "$var_name=\"\${input:-$default}\""
    else
        read -p "$(echo -e "${IRIDIUM}?${NC} ${prompt}: ")" input
        eval "$var_name=\"\$input\""
    fi
}

# Confirm action (returns 0 for yes, 1 for no)
confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local yn_prompt
    
    if [ "$default" = "y" ]; then
        yn_prompt="[${green}Y${NC}/n]"
    else
        yn_prompt="[y/${red}N${NC}]"
    fi
    
    read -p "$(echo -e "${yellow}?${NC} ${prompt} ${yn_prompt}: ")" -n 1 -r reply
    echo
    reply=${reply:-$default}
    
    [[ "$reply" =~ ^[Yy]$ ]]
}

# Wait with countdown (no Enter needed)
wait_seconds() {
    local seconds="${1:-3}"
    for ((i=seconds; i>0; i--)); do
        printf "\r${gray}Returning in ${i}s...${NC}"
        sleep 1
    done
    printf "\r                        \r"
}

get_system_info() {
    OS=$(lsb_release -d 2>/dev/null | awk -F'\t' '{print $2}')
    [ -z "$OS" ] && OS="Unknown"
    ARCH=$(uname -m)
    
    # Try to get IP info from ipapi.co
    IP_API_DATA=$(curl -s --connect-timeout 3 https://ipapi.co/json/ -4 2>/dev/null)
    if [ -n "$IP_API_DATA" ] && echo "$IP_API_DATA" | jq -e . >/dev/null 2>&1; then
        ISP=$(echo "$IP_API_DATA" | jq -r '.org // empty' 2>/dev/null)
        IP=$(echo "$IP_API_DATA" | jq -r '.ip // empty' 2>/dev/null)
    fi
    
    # Fallback for IP if still empty
    if [ -z "$IP" ]; then
        IP=$(curl -s --connect-timeout 3 -4 ip.sb 2>/dev/null)
    fi
    if [ -z "$IP" ]; then
        IP=$(curl -s --connect-timeout 3 -4 ifconfig.me 2>/dev/null)
    fi
    [ -z "$IP" ] && IP="N/A"
    [ -z "$ISP" ] && ISP="N/A"
    
    CPU=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $2 + $4 "%"}')
    [ -z "$CPU" ] && CPU="N/A"
    RAM=$(free -m 2>/dev/null | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
    [ -z "$RAM" ] && RAM="N/A"
}

version_greater_equal() {
    IFS='.' read -r -a local_version_parts <<< "$1"
    IFS='.' read -r -a latest_version_parts <<< "$2"

    for ((i=0; i<${#local_version_parts[@]}; i++)); do
        if [[ -z ${latest_version_parts[i]} ]]; then
            latest_version_parts[i]=0
        fi

        if ((10#${local_version_parts[i]} > 10#${latest_version_parts[i]})); then
            return 0
        elif ((10#${local_version_parts[i]} < 10#${latest_version_parts[i]})); then
            return 1
        fi
    done

    return 0
}

check_core_version() {
    if systemctl is-active --quiet hysteria-server.service; then
        HCVERSION=$(hysteria version | grep "^Version:" | awk '{print $2}')
        echo -e "Hysteria2 Core Version: ${cyan}$HCVERSION${NC}"
    fi
}

check_version() {
    local_version=$(cat $LOCALVERSION)
    latest_version=$(curl -s $LATESTVERSION)
    latest_changelog=$(curl -s $LASTESTCHANGE)

    if version_greater_equal "$local_version" "$latest_version"; then
        echo -e "Panel Version: ${cyan}$local_version${NC}"
    else
        echo -e "Panel Version: ${cyan}$local_version${NC}"
        echo -e "Latest Version: ${cyan}$latest_version${NC}"
        echo -e "${yellow}$latest_version Version Change Log:${NC}"
        echo -e "${cyan}$latest_changelog ${NC}"
    fi
}


load_hysteria2_env() {
    if [ -f "$CONFIG_ENV" ]; then
        export $(grep -v '^#' "$CONFIG_ENV" | xargs)
    else
        echo "Error: configs.env file not found. Using default SNI 'bts.com'."
        SNI="bts.com"
    fi
}

load_hysteria2_ips() {
    IP4=""
    IP6=""

    if [ -f "$CONFIG_ENV" ]; then
        IP4=$(grep -E "^IP4=" "$CONFIG_ENV" | cut -d '=' -f 2)
        IP6=$(grep -E "^IP6=" "$CONFIG_ENV" | cut -d '=' -f 2)
        
        if [[ -z "$IP4" || -z "$IP6" ]]; then
            default_interface=$(ip route | grep default | awk '{print $5}')
            
            if [ -n "$default_interface" ]; then
                if [ -z "$IP4" ]; then
                    system_IP4=$(ip addr show "$default_interface" | grep "inet " | awk '{print $2}' | cut -d '/' -f 1 | head -n 1)
                    if [ -n "$system_IP4" ]; then
                        IP4="$system_IP4"
                    else
                        system_IP4=$(curl -s -4 ip.sb)
                        [ -n "$system_IP4" ] && IP4="$system_IP4" || IP4="None"
                    fi
                fi
                
                if [ -z "$IP6" ]; then
                    system_IP6=$(ip addr show "$default_interface" | grep "inet6 " | awk '{print $2}' | grep -v "^fe80::" | cut -d '/' -f 1 | head -n 1)
                    if [ -n "$system_IP6" ]; then
                        IP6="$system_IP6"
                    else
                        system_IP6=$(curl -s -6 ip.sb)
                        [ -n "$system_IP6" ] && IP6="$system_IP6" || IP6="None"
                    fi
                fi
            else
                if [ -z "$IP4" ]; then
                    system_IP4=$(curl -s -4 ip.sb)
                    [ -n "$system_IP4" ] && IP4="$system_IP4" || IP4="None"
                fi
                if [ -z "$IP6" ]; then
                    system_IP6=$(curl -s -6 ip.sb)
                    [ -n "$system_IP6" ] && IP6="$system_IP6" || IP6="None"
                fi
            fi
        fi
    else
        # echo "Error: configs.env file not found. Fetching IPs from system..."
        default_interface=$(ip route | grep default | awk '{print $5}')
        
        if [ -n "$default_interface" ]; then
            system_IP4=$(ip addr show "$default_interface" | grep "inet " | awk '{print $2}' | cut -d '/' -f 1 | head -n 1)
            if [ -n "$system_IP4" ]; then
                IP4="$system_IP4"
            else
                system_IP4=$(curl -s -4 ip.sb)
                [ -n "$system_IP4" ] && IP4="$system_IP4" || IP4="None"
            fi
            
            system_IP6=$(ip addr show "$default_interface" | grep "inet6 " | awk '{print $2}' | grep -v "^fe80::" | cut -d '/' -f 1 | head -n 1)
            if [ -n "$system_IP6" ]; then
                IP6="$system_IP6"
            else
                system_IP6=$(curl -s -6 ip.sb)
                [ -n "$system_IP6" ] && IP6="$system_IP6" || IP6="None"
            fi
        else
            system_IP4=$(curl -s -4 ip.sb)
            [ -n "$system_IP4" ] && IP4="$system_IP4" || IP4="None"
            
            system_IP6=$(curl -s -6 ip.sb)
            [ -n "$system_IP6" ] && IP6="$system_IP6" || IP6="None"
        fi
        
        echo "IP4=$IP4" > "$CONFIG_ENV"
        echo "IP6=$IP6" >> "$CONFIG_ENV"
        return
    fi

    if grep -q "^IP4=" "$CONFIG_ENV"; then
        sed -i "s/^IP4=.*$/IP4=$IP4/" "$CONFIG_ENV"
    else
        echo "IP4=$IP4" >> "$CONFIG_ENV"
    fi
    
    if grep -q "^IP6=" "$CONFIG_ENV"; then
        sed -i "s/^IP6=.*$/IP6=$IP6/" "$CONFIG_ENV"
    else
        echo "IP6=$IP6" >> "$CONFIG_ENV"
    fi
}

