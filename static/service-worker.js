self.addEventListener('push', function(event) {
  console.log('Push event received:', event);

  const data = event.data.json();
  console.log('Push event data:', data);

  const options = {
      body: data.body,
      icon: data.icon,
      badge: data.badge,
  };

  event.waitUntil(
      self.registration.showNotification(data.title, options)
          .then(function() {
              console.log('Notification displayed:', data.title);
          }).catch(function(error) {
              console.log('Error displaying notification:', error);
          })
  );
});
