pragma solidity ^0.8.18;

contract OrderContract {

    enum State {Created, Paid, PickedUp, Delivered}

    address public owner;
    address public customer;
    address public courier;

    uint256 public amountWei;
    State public state;

    event Paid(address indexed customer, uint256 value);
    event CourierBound(address indexed courier);
    event Delivered(uint256 toOwner, uint256 toCourier);

    constructor(address _owner, address _customer, uint256 _amountWei) {
        require(_owner != address(0) && _customer != address(0), "Neispravna adresa");
        require(_amountWei > 0, "Neispravan iznos");
        owner = _owner;
        customer = _customer;
        amountWei = _amountWei;
        state = State.Created;
    }

    receive() external payable {
        require(state == State.Created, "Vec je uplaceno");
        require(msg.sender == customer, "Neispravan vlasnik ugovora");
        require(msg.value == amountWei, "Neispravan iznos");
        state = State.Paid;
        emit Paid(msg.sender, msg.value);
    }

    function pickUp(address _courier) external {
        require(state == State.Paid, "Nije placeno, ili je vec preuzeto");
        require(msg.sender == owner, "Nije poslao vlasnik");
        require(_courier != address(0), "Neispravna adresa kurira");
        state = State.PickedUp;
        courier = _courier;
        emit CourierBound(_courier);
    }

    function finaliseDelivery() external {
        require(state == State.PickedUp, "Nije preuzeto ili je vec dostavljeno");
        require(msg.sender == owner, "Nema pristupa ovome");
        require(courier != address(0), "Kurir nije preuzeo jos");
        uint256 toOwner = (amountWei * 80) / 100;
        uint256 toCourier = amountWei - toOwner;
        state = State.Delivered;

        (bool ok1, ) = owner.call{value: toOwner}("");
        (bool ok2, ) = courier.call{value: toCourier}("");
        require(ok1 && ok2, "payout failed");

        emit Delivered(toOwner, toCourier);
    }

    function isPaid() public view returns (bool) {
        return state == State.Paid || state == State.PickedUp || state == State.Delivered;
    }

    function isPickedUp() public view returns (bool) {
        return state == State.PickedUp || state == State.Delivered;
    }

    function isDelivered() public view returns (bool) {
        return state == State.Delivered;
    }

}