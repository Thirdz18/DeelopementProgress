// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title GamesRewards
 * @dev Smart Contract for Minigames G$ Rewards Disbursement
 * @notice Replaces direct GAMES_KEY transfers with a secure vault contract
 * @author GoodMarket Development Team
 * 
 * Features:
 * - Owner-only disbursement for security
 * - Daily limits per user
 * - Event logging for transparency
 * - Emergency pause functionality
 * - Anti-reentrancy protection
 */
contract GamesRewards {
    // ============ STATE VARIABLES ============
    
    /// @notice G$ Token contract address
    address public immutable token;
    
    /// @notice Contract owner (admin address)
    address public owner;
    
    /// @notice Emergency pause flag
    bool public paused;
    
    /// @notice Daily disbursement limit per user (in wei)
    uint256 public dailyLimitPerUser;
    
    /// @notice Total rewards disbursed (for tracking)
    uint256 public totalRewardsDisbursed;
    
    // ============ MAPPINGS ============
    
    /// @notice Track last claim timestamp per user
    mapping(address => uint256) public lastClaimTimestamp;
    
    /// @notice Track daily claimed amount per user
    mapping(address => uint256) public dailyClaimedAmount;
    
    /// @notice Track total claimed per user
    mapping(address => uint256) public totalClaimedByUser;
    
    /// @notice Whitelist for authorized disbursers (backend server)
    mapping(address => bool) public authorizedDisbursers;
    
    // ============ EVENTS ============
    
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event Disbursement(
        address indexed recipient, 
        uint256 amount, 
        address indexed disburser,
        string sessionId,
        uint256 gasUsed
    );
    event DailyLimitUpdated(uint256 newLimit);
    event EmergencyPauseToggled(bool paused);
    event AuthorizedDisburserUpdated(address indexed disburser, bool authorized);
    event TokensWithdrawnByOwner(address indexed recipient, uint256 amount);
    
    // ============ ERRORS ============
    
    error NotOwner();
    error NotAuthorizedDisburser();
    error ContractPaused();
    error DailyLimitExceeded();
    error ZeroAmount();
    error TransferFailed();
    error InsufficientBalance();
    
    // ============ MODIFIERS ============
    
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }
    
    modifier onlyAuthorized() {
        if (paused) revert ContractPaused();
        if (!authorizedDisbursers[msg.sender] && msg.sender != owner) revert NotAuthorizedDisburser();
        _;
    }
    
    modifier nonZeroAmount(uint256 amount) {
        if (amount == 0) revert ZeroAmount();
        _;
    }
    
    // ============ CONSTRUCTOR ============
    
    /**
     * @param _token G$ Token contract address
     * @param _owner Initial owner address
     * @param _dailyLimit Initial daily limit per user (in wei)
     */
    constructor(
        address _token, 
        address _owner, 
        uint256 _dailyLimit
    ) {
        require(_token != address(0), "Token address cannot be zero");
        require(_owner != address(0), "Owner address cannot be zero");
        
        token = _token;
        owner = _owner;
        dailyLimitPerUser = _dailyLimit;
        paused = false;
        
        // Authorize owner by default
        authorizedDisbursers[_owner] = true;
        
        emit OwnershipTransferred(address(0), _owner);
        emit DailyLimitUpdated(_dailyLimit);
    }
    
    // ============ CORE FUNCTIONS ============
    
    /**
     * @notice Disburse rewards to a user (called by authorized backend)
     * @param recipient User wallet address to receive rewards
     * @param amount Amount of G$ to disburse (in wei)
     * @param sessionId Game session ID for tracking
     * @return success True if successful
     */
    function disburseReward(
        address recipient, 
        uint256 amount, 
        string calldata sessionId
    ) 
        external 
        onlyAuthorized 
        nonZeroAmount(amount) 
        returns (bool success) 
    {
        // Check daily limit
        _checkAndUpdateDailyLimit(recipient, amount);
        
        // Update totals
        dailyClaimedAmount[recipient] += amount;
        totalClaimedByUser[recipient] += amount;
        totalRewardsDisbursed += amount;
        
        // Emit event BEFORE transfer (for transparency)
        emit Disbursement(recipient, amount, msg.sender, sessionId, gasleft());
        
        // Transfer tokens
        success = _safeTransfer(recipient, amount);
        
        require(success, "Token transfer failed");
    }
    
    /**
     * @notice Batch disburse to multiple users (gas efficient)
     * @param recipients Array of recipient addresses
     * @param amounts Array of amounts (must match recipients length)
     * @param sessionIds Array of session IDs for tracking
     */
    function batchDisburse(
        address[] calldata recipients,
        uint256[] calldata amounts,
        string[] calldata sessionIds
    ) external onlyAuthorized {
        require(recipients.length == amounts.length, "Length mismatch");
        require(recipients.length == sessionIds.length, "Length mismatch");
        
        for (uint256 i = 0; i < recipients.length; i++) {
            if (amounts[i] > 0) {
                _checkAndUpdateDailyLimit(recipients[i], amounts[i]);
                dailyClaimedAmount[recipients[i]] += amounts[i];
                totalClaimedByUser[recipients[i]] += amounts[i];
                totalRewardsDisbursed += amounts[i];
                
                emit Disbursement(recipients[i], amounts[i], msg.sender, sessionIds[i], gasleft());
                require(_safeTransfer(recipients[i], amounts[i]), "Transfer failed");
            }
        }
    }
    
    /**
     * @notice Check and update daily limit for a user
     * @param user User address
     * @param amount Amount to claim
     */
    function _checkAndUpdateDailyLimit(address user, uint256 amount) internal {
        // Reset daily counter if 24 hours have passed
        if (block.timestamp >= lastClaimTimestamp[user] + 24 hours) {
            dailyClaimedAmount[user] = amount;
            lastClaimTimestamp[user] = block.timestamp;
        } else {
            // Check if adding this amount would exceed daily limit
            if (dailyClaimedAmount[user] + amount > dailyLimitPerUser) {
                revert DailyLimitExceeded();
            }
            dailyClaimedAmount[user] += amount;
        }
    }
    
    /**
     * @notice Safe transfer with error handling
     */
    function _safeTransfer(address to, uint256 amount) internal returns (bool) {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSignature("transfer(address,uint256)", to, amount)
        );
        return success && (data.length == 0 || abi.decode(data, (bool)));
    }
    
    // ============ OWNER FUNCTIONS ============
    
    /**
     * @notice Transfer ownership
     * @param newOwner New owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero");
        address previousOwner = owner;
        owner = newOwner;
        
        // Update authorization
        authorizedDisbursers[previousOwner] = false;
        authorizedDisbursers[newOwner] = true;
        
        emit OwnershipTransferred(previousOwner, newOwner);
    }
    
    /**
     * @notice Update authorized disburser status
     * @param disburser Address to update
     * @param authorized New authorization status
     */
    function setAuthorizedDisburser(address disburser, bool authorized) external onlyOwner {
        require(disburser != address(0), "Disburser cannot be zero");
        authorizedDisbursers[disburser] = authorized;
        emit AuthorizedDisburserUpdated(disburser, authorized);
    }
    
    /**
     * @notice Update daily limit per user
     * @param newLimit New daily limit (in wei)
     */
    function updateDailyLimit(uint256 newLimit) external onlyOwner {
        dailyLimitPerUser = newLimit;
        emit DailyLimitUpdated(newLimit);
    }
    
    /**
     * @notice Toggle emergency pause
     * @param _paused New pause state
     */
    function setPaused(bool _paused) external onlyOwner {
        paused = _paused;
        emit EmergencyPauseToggled(_paused);
    }
    
    /**
     * @notice Withdraw tokens by owner (for contract funding)
     * @param recipient Address to send tokens to
     * @param amount Amount to withdraw
     */
    function withdrawTokens(address recipient, uint256 amount) external onlyOwner nonZeroAmount(amount) {
        require(IERC20(token).balanceOf(address(this)) >= amount, "Insufficient balance");
        
        emit TokensWithdrawnByOwner(recipient, amount);
        require(_safeTransfer(recipient, amount), "Transfer failed");
    }
    
    // ============ VIEW FUNCTIONS ============
    
    /**
     * @notice Get user's claimable amount today
     * @param user User address
     * @return claimable Amount user can still claim today
     */
    function getRemainingDailyLimit(address user) external view returns (uint256 claimable) {
        if (block.timestamp >= lastClaimTimestamp[user] + 24 hours) {
            return dailyLimitPerUser;
        }
        
        if (dailyClaimedAmount[user] >= dailyLimitPerUser) {
            return 0;
        }
        
        return dailyLimitPerUser - dailyClaimedAmount[user];
    }
    
    /**
     * @notice Get user statistics
     * @param user User address
     * @return total Total claimed by user
     * @return dailyToday Amount claimed today
     * @return lastClaim Last claim timestamp
     */
    function getUserStats(address user) external view returns (
        uint256 total, 
        uint256 dailyToday, 
        uint256 lastClaim
    ) {
        // Reset daily if needed for accurate view
        if (block.timestamp >= lastClaimTimestamp[user] + 24 hours) {
            dailyToday = 0;
        } else {
            dailyToday = dailyClaimedAmount[user];
        }
        
        return (
            totalClaimedByUser[user],
            dailyToday,
            lastClaimTimestamp[user]
        );
    }
    
    /**
     * @notice Get contract balance
     */
    function getContractBalance() external view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }
    
    // ============ RECEIVE FUNCTION ============
    
    /// @notice Allow contract to receive native tokens (for gas refund)
    receive() external payable {}
}

/**
 * @title IERC20
 * @dev Minimal ERC20 interface
 */
interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function decimals() external view returns (uint8);
}
